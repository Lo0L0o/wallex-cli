from argparse import Namespace
from typing import Any

from market.application.container import ApplicationContainer


def register(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "price",
        help="show one saved price",
    )
    parser.add_argument("symbol")
    parser.set_defaults(run_command=run)


async def run(args: Namespace, app: ApplicationContainer) -> int:
    price = await app.get_price.execute(args.symbol)

    if price is None:
        print(f"No market found for: {args.symbol}")
        return 0

    print(f"{args.symbol}\t{price}")
    return 0