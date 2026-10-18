import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    market_api_url: str
    database_driver: str
    sqlite_path: str
    mysql: dict[str, object]
    redis_url: str = "redis://127.0.0.1:6379/0"
    sync_interval: int = 600
    cache_ttl: int = 60
    web_host: str = "127.0.0.1"
    web_port: int = 8000

    @classmethod
    def from_environment(cls) -> "Settings":
        driver = os.getenv("DB_DRIVER", "sqlite").lower()
        if driver not in {"sqlite", "mysql"}:
            raise ValueError("DB_DRIVER must be 'sqlite' or 'mysql'")
        interval = int(os.getenv("SYNC_INTERVAL_SECONDS", "600"))
        ttl = int(os.getenv("CACHE_TTL_SECONDS", "60"))
        if not 1 <= interval <= 600:
            raise ValueError("SYNC_INTERVAL_SECONDS must be between 1 and 600")
        if not 1 <= ttl <= 60:
            raise ValueError("CACHE_TTL_SECONDS must be between 1 and 60")
        return cls(
            market_api_url=os.getenv(
                "MARKET_API_URL", "https://api.wallex.ir/hector/web/v1/markets"
            ),
            database_driver=driver,
            sqlite_path=os.getenv("SQLITE_PATH", "market.db"),
            mysql={
                "host": os.getenv("DB_HOST", "localhost"),
                "port": int(os.getenv("DB_PORT", "3306")),
                "user": os.getenv("DB_USER", "market_app"),
                "password": os.getenv("DB_PASSWORD", ""),
                "database": os.getenv("DB_NAME", "market_data"),
                "connection_timeout": int(os.getenv("DB_CONNECTION_TIMEOUT", "5")),
            },
            redis_url=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
            sync_interval=interval,
            cache_ttl=ttl,
            web_host=os.getenv("WEB_HOST", "127.0.0.1"),
            web_port=int(os.getenv("WEB_PORT", "8000")),
        )
