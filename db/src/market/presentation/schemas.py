from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MarketQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    search: str = Field(default="", max_length=50)
    quote: str = Field(default="USDT", pattern=r"^(USDT|TMN)$")
    limit: int = Field(default=10, ge=1, le=100)
    featured: bool = False

    @field_validator("search", "quote", mode="before")
    @classmethod
    def normalize(cls, value):
        return value.strip().upper() if isinstance(value, str) else value


class SymbolQuery(BaseModel):
    symbol: str = Field(pattern=r"^[A-Z0-9]{1,50}$")

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize(cls, value):
        return value.strip().upper() if isinstance(value, str) else value


class HistoryQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(default=100, ge=1, le=500)


class MarketResponse(BaseModel):
    symbol: str
    price: Decimal
    quote_asset: str
    quote_volume: Decimal


class HistoryPointResponse(BaseModel):
    price: Decimal
    recorded_at: datetime
