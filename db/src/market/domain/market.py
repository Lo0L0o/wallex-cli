from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Market:
    symbol: str
    price: Decimal

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("Market symbol cannot be empty")
        if not self.price.is_finite() or self.price < 0:
            raise ValueError("Market price must be a finite, non-negative number")

