from argparse import Namespace
from typing import Any
from market.application.container import ApplicationContainer


def register(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "search",
        help="search saved markets",
    )
    parser.add_argument("query")
    parser.set_defaults(run_command=run)


async def run(args: Namespace, app: ApplicationContainer) -> int:
    markets = await app.search_markets.execute(args.query)

    if not markets:
        print(f"No markets found for: {args.query}")
        return 0

    for market in markets:
        print(f"{market.symbol}\t{market.price}")

    return 0