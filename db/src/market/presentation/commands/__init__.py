"""CLI command registration point; add a command module here."""

from typing import Any

from market.presentation.commands import list_markets, price, search, sync


def register_commands(subparsers: Any) -> None:
    """Register command modules here when adding a CLI feature."""
    sync.register(subparsers)
    list_markets.register(subparsers)
    search.register(subparsers)
    price.register(subparsers)

