from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MarketRow(Base):
    __tablename__ = "market"

    symbol: Mapped[str] = mapped_column(String(50), primary_key=True)
    price: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[str] = mapped_column(Text, server_default=text("CURRENT_TIMESTAMP"))
    quote_asset: Mapped[str] = mapped_column(String(10), server_default="")
    quote_volume: Mapped[str] = mapped_column(Text, server_default="0")


class PriceRow(Base):
    __tablename__ = "price_history"
    __table_args__ = (Index("ix_history_symbol_id", "symbol", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(ForeignKey("market.symbol"))
    price: Mapped[str] = mapped_column(Text)
    recorded_at: Mapped[str] = mapped_column(Text)


class SyncRow(Base):
    __tablename__ = "sync_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_success: Mapped[float] = mapped_column(Float, server_default="0")
    last_attempt: Mapped[float] = mapped_column(Float, server_default="0")
    lease_until: Mapped[float] = mapped_column(Float, server_default="0")
    token: Mapped[str | None] = mapped_column(String(32), nullable=True)
