import json
import logging
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from time import perf_counter
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4
from urllib.error import URLError

from market.infrastructure.providers.wallex_http_client import fetch_markets


logger = logging.getLogger("market.http")


class Handler(BaseHTTPRequestHandler):
    def handle_one_request(self):
        self.started = perf_counter()
        self.request_id = uuid4().hex
        super().handle_one_request()

    def parse_request(self):
        valid = super().parse_request()
        if valid:
            supplied = self.headers.get("X-Request-ID", "")
            if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", supplied):
                self.request_id = supplied
        return valid

    def send_json(self, status, data):
        if "error" in data:
            data["error"]["request_id"] = self.request_id
        body = json.dumps(data).encode("utf-8")
        duration = round((perf_counter() - self.started) * 1000, 2)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Request-ID", self.request_id)
        self.send_header("X-Process-Time-Ms", str(duration))
        if status == 405:
            self.send_header("Allow", "GET")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
        path = urlsplit(self.path).path
        if path.startswith("/api/v1/markets/"):
            path = "/api/v1/markets/{symbol}"
        logger.info(json.dumps({
            "request_id": self.request_id,
            "method": self.command,
            "path": path if path in {"/health", "/api/v1/markets", "/api/v1/markets/{symbol}"} else "<unmatched>",
            "status": status,
            "duration_ms": duration,
            "error_category": data.get("error", {}).get("code"),
        }))

    def send_error(self, code, message=None, explain=None):
        if code == 501:
            self.method_not_allowed()
            return
        self.send_json(code, {"error": {
            "code": "http_error", "message": self.responses.get(code, ("HTTP error",))[0],
        }})

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == "/health":
            self.send_json(200, {"status": "ok"})
        elif url.path == "/api/v1/markets" or url.path.startswith("/api/v1/markets/"):
            self.market_response(url)
        else:
            self.send_json(404, {"error": {"code": "not_found", "message": "Not found"}})

    def market_response(self, url):
        symbol = None
        if url.path != "/api/v1/markets":
            symbol = url.path.removeprefix("/api/v1/markets/").upper()
            if not re.fullmatch(r"[A-Z0-9]{1,40}", symbol):
                self.send_json(400, {"error": {"code": "bad_request", "message": "Invalid symbol"}})
                return
        try:
            markets = fetch_markets(self.request_id)
        except (TimeoutError, URLError) as error:
            timed_out = isinstance(error, TimeoutError) or isinstance(getattr(error, "reason", None), TimeoutError)
            self.send_json(504 if timed_out else 502, {"error": {
                "code": "provider_timeout" if timed_out else "provider_unavailable",
                "message": "Could not get markets from Wallex",
            }})
            return
        except (ValueError, KeyError, TypeError, AttributeError):
            self.send_json(502, {"error": {"code": "invalid_provider_response", "message": "Invalid Wallex response"}})
            return

        if symbol:
            for market in markets:
                if market.symbol.upper() == symbol:
                    self.send_json(200, {"symbol": market.symbol, "price": str(market.price)})
                    return
            self.send_json(404, {"error": {"code": "market_not_found", "message": "Market not found"}})
            return

        query = parse_qs(url.query).get("search", [""])[0].upper()
        items = [{"symbol": m.symbol, "price": str(m.price)}
                 for m in markets if query in m.symbol.upper()]
        self.send_json(200, {"items": items, "total": len(items)})

    def method_not_allowed(self):
        self.send_json(405, {"error": {"code": "method_not_allowed", "message": "Use GET"}})

    do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_HEAD = method_not_allowed

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print("Learning HTTP server: http://127.0.0.1:8001 (Ctrl+C to stop)")
    with HTTPServer(("127.0.0.1", 8001), Handler) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
