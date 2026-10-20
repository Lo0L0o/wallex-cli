import asyncio
import json
import logging
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.routing import Route

from market.application.container import ApplicationContainer
from market.config import Settings
from market.domain.monitor import MarketUnavailable
from market.infrastructure.persistence.models import SyncRow
from market.presentation.schemas import (
    HistoryPointResponse,
    HistoryQuery,
    MarketQuery,
    MarketResponse,
    SymbolQuery,
)

logger = logging.getLogger("market.web")
static = Path(__file__).with_name("static")
featured_assets = ("BTC", "ETH", "BNB", "SOL", "XRP", "DOGE", "ADA", "TRX", "DOT", "AVAX")


def error_response(request: Request, status: int, code: str, message: str, details=None):
    error = {"code": code, "message": message, "request_id": request.state.request_id}
    if details is not None:
        error["details"] = details
    return JSONResponse({"error": error}, status_code=status)


def market_data(market):
    return MarketResponse(
        symbol=market.symbol,
        price=market.price,
        quote_asset=market.quote_asset,
        quote_volume=market.quote_volume,
    ).model_dump(mode="json")


def metadata(result):
    stamp = result.snapshot.updated_at
    return {
        "updated_at": stamp.isoformat() if stamp else None,
        "source": result.source,
        "stale": result.stale,
    }


async def markets(request: Request):
    query = MarketQuery.model_validate(dict(request.query_params))
    result = await request.app.state.container.monitor.current()
    matches = [
        m
        for m in result.snapshot.markets
        if m.quote_asset == query.quote and query.search in m.symbol
    ]
    if query.featured:
        symbols = [asset + query.quote for asset in featured_assets]
        by_symbol = {m.symbol: m for m in matches}
        matches = [by_symbol[symbol] for symbol in symbols if symbol in by_symbol]
    else:
        matches.sort(key=lambda m: (-m.quote_volume, m.symbol))
    return JSONResponse(
        {
            "items": [market_data(m) for m in matches[: query.limit]],
            "total": len(matches),
            "quote": query.quote,
            "ranking": "featured" if query.featured else "quote_volume_24h",
            **metadata(result),
        }
    )


async def market_detail(request: Request):
    symbol = SymbolQuery(symbol=request.path_params["symbol"]).symbol
    result = await request.app.state.container.monitor.current()
    market = next((m for m in result.snapshot.markets if m.symbol == symbol), None)
    if market is None:
        raise HTTPException(404, "Market not found")
    return JSONResponse({**market_data(market), **metadata(result)})


async def market_history(request: Request):
    symbol = SymbolQuery(symbol=request.path_params["symbol"]).symbol
    query = HistoryQuery.model_validate(dict(request.query_params))
    container = request.app.state.container
    if await container.get_price.execute(symbol) is None:
        raise HTTPException(404, "Market not found")
    points = await container.monitor.repository.history(symbol, query.limit)
    return JSONResponse(
        {
            "symbol": symbol,
            "points": [
                HistoryPointResponse(price=p.price, recorded_at=p.recorded_at).model_dump(
                    mode="json"
                )
                for p in points
            ],
        }
    )


async def health(request: Request):
    container = request.app.state.container
    async with container.database.sessions() as session:
        await session.execute(select(SyncRow.id))
    return JSONResponse({"status": "ok"})


async def website(request: Request):
    return FileResponse(static / "index.html")


async def search_page(request: Request):
    return FileResponse(static / "search.html")


async def website_asset(request: Request):
    name = request.path_params["name"]
    if name not in {"app.js", "style.css"}:
        raise HTTPException(404, "File not found")
    return FileResponse(static / name)


async def home(request: Request):
    return RedirectResponse("/website/")


def create_app(settings: Settings | None = None, container=None, schedule: bool = True):
    settings = settings or Settings.from_environment()

    @asynccontextmanager
    async def lifespan(app):
        if settings.database_driver != "sqlite":
            raise RuntimeError("The web monitor uses SQLite ORM. Set DB_DRIVER=sqlite.")
        app.state.container = container or ApplicationContainer(settings)
        scheduler = None
        try:
            try:
                async with app.state.container.database.sessions() as session:
                    await session.execute(select(SyncRow.id))
            except SQLAlchemyError as error:
                raise RuntimeError(
                    "Database migration required: run alembic upgrade head"
                ) from error
            if schedule:
                scheduler = AsyncIOScheduler(timezone="UTC")
                scheduler.add_job(
                    app.state.container.monitor.scheduled_sync,
                    "interval",
                    seconds=settings.sync_interval,
                    id="wallex-sync",
                    max_instances=1,
                    coalesce=True,
                    next_run_time=datetime.now(timezone.utc),
                )
                scheduler.start()
            app.state.scheduler = scheduler
            yield
        finally:
            if scheduler is not None:
                scheduler.pause()
                await app.state.container.monitor.wait_idle()
                scheduler.shutdown(wait=False)
                await asyncio.sleep(0)
            await app.state.container.close()

    routes = [
        Route("/", home),
        Route("/health", health),
        Route("/website/", website),
        Route("/website/search", search_page),
        Route("/website/assets/{name}", website_asset),
        Route("/api/v1/markets", markets),
        Route("/api/v1/markets/{symbol}/history", market_history),
        Route("/api/v1/markets/{symbol}", market_detail),
    ]

    async def request_log(request: Request, call_next):
        started = perf_counter()
        supplied = request.headers.get("X-Request-ID", "")
        request.state.request_id = (
            supplied if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", supplied) else uuid4().hex
        )
        try:
            response = await call_next(request)
        except ValidationError as error:
            response = error_response(
                request,
                422,
                "invalid_input",
                "Check request parameters",
                error.errors(include_url=False, include_context=False, include_input=False),
            )
        except MarketUnavailable as error:
            response = error_response(request, 503, "market_unavailable", str(error))
        except Exception:
            logger.exception("Request failed")
            response = error_response(
                request, 503, "service_unavailable", "Please try again shortly"
            )
        elapsed = round((perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Process-Time-Ms"] = str(elapsed)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'"
        )
        route = request.scope.get("route")
        logger.info(
            json.dumps(
                {
                    "request_id": request.state.request_id,
                    "method": request.method,
                    "route": route.path if route else "<unmatched>",
                    "status": response.status_code,
                    "duration_ms": elapsed,
                }
            )
        )
        return response

    async def http_error(request, error):
        response = error_response(request, error.status_code, "http_error", str(error.detail))
        if error.headers:
            response.headers.update(error.headers)
        return response

    return Starlette(
        routes=routes,
        lifespan=lifespan,
        middleware=[Middleware(BaseHTTPMiddleware, dispatch=request_log)],
        exception_handlers={HTTPException: http_error},
    )


def serve():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = Settings.from_environment()
    uvicorn.run(create_app(settings), host=settings.web_host, port=settings.web_port)


if __name__ == "__main__":
    serve()
