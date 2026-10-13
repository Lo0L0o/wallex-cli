# Market CLI learning project

## Week 2 - Day 8: HTTP server (standard library only)

Run from the project folder in PowerShell. No extra packages are needed:

```powershell
$env:PYTHONPATH = "src"
python -m market.presentation.http_server
```

Open `http://127.0.0.1:8001/health` or
`http://127.0.0.1:8001/api/v1/markets/BTCUSDT`. Stop the server with Ctrl+C.
Each market request fetches live data from Wallex without changing the database.
GET /api/v1/markets lists markets; ?search=BTC filters symbols;
GET /api/v1/markets/BTCUSDT returns one price as a decimal string.

Inspect headers and success/failure responses in another terminal:

```powershell
curl.exe -i http://127.0.0.1:8001/health
curl.exe -i -H "X-Request-ID: lesson-8" "http://127.0.0.1:8001/api/v1/markets?search=BTC"
curl.exe -i "http://127.0.0.1:8001/api/v1/markets/!"
curl.exe -i http://127.0.0.1:8001/missing
curl.exe -i -X POST http://127.0.0.1:8001/health
```

Expected statuses: 200, 200, 400, 404, 405. The invalid symbol is the controlled
application error. Errors share a JSON shape:
`{"error":{"code":"...","message":"...","request_id":"..."}}`.
Wallex connection failures return 502; timeouts return 504.
Every response includes `X-Request-ID` and `X-Process-Time-Ms`.
The server accepts a request ID containing 1-64 letters, digits, underscores
or hyphens; otherwise it creates one. JSON logs include method, normalized
path, status, elapsed milliseconds and error category, but never credentials,
query strings or request bodies.

Request flow: parse HTTP request -> assign request ID -> match method/path ->
handler -> serialize JSON -> add headers and log -> send response.
The shared request/response hooks illustrate the responsibility of middleware.
Business rules still belong in application services, not these hooks.
GET reads a resource; query parameters customize/filter a request. HTTP
headers and status describe the response; JSON is its application payload.
Authentication identifies a caller; authorization decides what they can do.
Input validation does neither. This lab does not add authentication.

This synchronous `HTTPServer` processes one request at a time and is for
learning, not production deployment. Async is useful for non-blocking I/O;
blocking work inside an async handler would stall its event loop. In Django,
the equivalent responsibilities are the server, middleware, URLconf, view,
service and response.

Run the local checks with `python -m unittest discover -s tests`.

This repository is the application root. The Python package is `market` under
`src/`; there is no nested `market_cli/` package. The project teaches Python,
application lifecycle, and a small practical DDD structure without a web
framework.

The `sync` command is the complete happy path. Students can extend the
registered commands, application use cases, database adapters, and external
service providers without putting all behavior into one file.

## Structure

```text
src/market/
  domain/                 Market entity and repository/provider contracts
  application/            Use cases and dependency composition
  infrastructure/
    persistence/          SQLite and MySQL implementations
    providers/             HTTP market service implementation
  presentation/            CLI parser and command registration
  config.py                Environment-based settings
  main.py                  Process entry point and lifecycle
```

- **Domain** holds business concepts and contracts. It does not import database,
  HTTP, or CLI libraries.
- **Application** coordinates domain contracts in use cases. `container.py` is
  the composition root that chooses concrete adapters.
- **Infrastructure** contains backend-specific SQL and external service code.
- **Presentation** handles command-line arguments and user-facing output.
- **main.py** owns process startup, execution, error reporting, cleanup, and exit
  status.

## Database backends

SQLite is the default and needs no database server. Its adapter is
`SQLiteMarketRepository`. To use MySQL, set `DB_DRIVER=mysql` and provide the
`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME` settings. The MySQL
adapter implements the same `MarketRepository` contract, while keeping its own
connection settings, SQL placeholders, table definition, upsert statement, and
transaction handling. Add another database by implementing that contract and
selecting the adapter in `ApplicationContainer._create_repository`.

The two adapters are alternatives selected per run. If students need to write
to multiple databases in one run, add a composite repository in infrastructure
that delegates each operation to the selected repositories.

## Run

Use Python 3.10 or newer:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
market-cli sync
```

To choose MySQL, export its settings before running:

```sh
export DB_DRIVER=mysql DB_HOST=localhost DB_PORT=3306
export DB_USER=market_app DB_PASSWORD='your-password' DB_NAME=market_data
market-cli sync
```

You can also run the module directly from the source tree:

```sh
PYTHONPATH=src python -m market.main sync
```

`MARKET_API_URL` can point to a compatible API. The default URL is the example
market service configured in `config.py`.

## Follow the happy path

1. `main.py` parses arguments and loads settings.
2. `ApplicationContainer` creates the HTTP provider and configured database
   repository.
3. The registered `sync` command calls the `SyncMarkets` use case.
4. The use case asks the provider for `Market` entities and passes them to the
   repository contract.
5. The selected persistence adapter writes them using its database's own logic.
6. The CLI reports the count and `main.py` closes external resources.

## Extend the project

### Add a command

Add a module in `presentation/commands/` with `register()` and `run()` functions,
then import and register the module in `presentation/commands/__init__.py`. Put
the behavior in its own application use case and expose that use case through
`ApplicationContainer`. The parser passes parsed arguments and the container to
the command function.

### Add business behavior

Put the operation in an application use case. Add or update domain entities and
contracts when the business rules need them. Keep SQL and HTTP requests in
infrastructure adapters so the use case does not depend on a specific vendor.

### Add an external service

Define its contract in `domain/`, implement it under
`infrastructure/providers/`, then construct and inject it in
`ApplicationContainer`. Existing use cases can depend on the contract and do
not need to know which provider is selected.

### Student exercises

- Implement `markets`, `search`, and `price` with separate application use
  cases, then connect the CLI commands.
- Add input validation and useful messages for missing symbols or empty results.
- Add a third database adapter and select it with a configuration setting.
- Add an in-memory provider or repository for experimenting without external
  services.
