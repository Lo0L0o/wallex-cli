from argparse import Namespace
from typing import Any

from market.application.container import ApplicationContainer


def register(subparsers: Any) -> None:
    parser = subparsers.add_parser("markets", help="list saved markets")
    parser.set_defaults(run_command=run)


async def run(args: Namespace, app: ApplicationContainer) -> int:
    markets = await app.list_markets.execute()
    if not markets:
        print("No saved markets. Run sync first.")
        return 0

    for market in markets:
        print(f"{market.symbol}\t{market.price}")
    return 0
