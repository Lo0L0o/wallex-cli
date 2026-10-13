import json
import sys
import threading
import unittest
from http.client import HTTPConnection
from http.server import HTTPServer
from pathlib import Path
from unittest.mock import patch
from decimal import Decimal
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from market.presentation.http_server import Handler
from market.domain.market import Market


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.provider = patch("market.presentation.http_server.fetch_markets", return_value=[
            Market("BTCUSDT", Decimal("123.45")), Market("ETHUSDT", Decimal("20"))])
        self.fetch = self.provider.start()
        self.addCleanup(self.provider.stop)

    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, path, method="GET", headers=None):
        connection = HTTPConnection(*self.server.server_address, timeout=3)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            data = response.read()
            return response.status, dict(response.getheaders()), json.loads(data) if data else None
        finally:
            connection.close()

    def test_success_and_query(self):
        status, headers, body = self.request("/health")
        self.assertEqual((status, body), (200, {"status": "ok"}))
        self.assertIn("application/json", headers["Content-Type"])
        self.assertGreaterEqual(float(headers["X-Process-Time-Ms"]), 0)
        self.assertEqual(self.request("/api/v1/markets?search=BTC")[2]["total"], 1)
        self.assertEqual(self.request("/api/v1/markets/BTCUSDT")[2], {"symbol": "BTCUSDT", "price": "123.45"})

    def test_errors_and_ids(self):
        for path, method, expected in [("/api/v1/markets/!", "GET", 400),
                                       ("/api/v1/markets/UNKNOWN", "GET", 404),
                                       ("/missing", "GET", 404),
                                       ("/health", "POST", 405),
                                       ("/health", "CUSTOM", 405)]:
            status, headers, body = self.request(path, method, {"X-Request-ID": "lesson-8"})
            self.assertEqual(status, expected)
            self.assertEqual(headers["X-Request-ID"], "lesson-8")
            self.assertEqual(body["error"]["request_id"], "lesson-8")
            if expected == 405:
                self.assertEqual(headers["Allow"], "GET")

    def test_unsafe_id_and_private_logs(self):
        with self.assertLogs("market.http", level="INFO") as captured:
            _, headers, _ = self.request("/api/v1/markets?search=SECRET", headers={
                "X-Request-ID": "invalid id", "Authorization": "Bearer PRIVATE"})
        self.assertRegex(headers["X-Request-ID"], r"^[a-f0-9]{32}$")
        record = json.loads(captured.records[0].getMessage())
        self.assertEqual(record["path"], "/api/v1/markets")
        self.assertNotIn("SECRET", captured.output[0])
        self.assertNotIn("PRIVATE", captured.output[0])

    def test_head_has_no_body(self):
        status, headers, body = self.request("/health", "HEAD")
        self.assertEqual(status, 405)
        self.assertIsNone(body)

    def test_provider_failures(self):
        for error, status in [(URLError("offline"), 502), (TimeoutError(), 504), (ValueError("bad data"), 502)]:
            self.fetch.side_effect = error
            result = self.request("/api/v1/markets")
            self.assertEqual(result[0], status)
            self.assertEqual(result[2]["error"]["request_id"], result[1]["X-Request-ID"])
