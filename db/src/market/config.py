import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    market_api_url: str
    database_driver: str
    sqlite_path: str
    mysql: dict[str, object]

    @classmethod
    def from_environment(cls) -> "Settings":
        driver = os.getenv("DB_DRIVER", "sqlite").lower()
        if driver not in {"sqlite", "mysql"}:
            raise ValueError("DB_DRIVER must be 'sqlite' or 'mysql'")
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
        )

