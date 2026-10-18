# Market Monitor

Run from this folder in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\alembic.exe upgrade head
$env:WEB_PORT = "8000"
.\.venv\Scripts\market-web.exe
```

Open http://127.0.0.1:8000/website/.

Redis (optional for local use): `docker compose up -d redis`.
Without Redis, the application reads saved prices from SQLite.
