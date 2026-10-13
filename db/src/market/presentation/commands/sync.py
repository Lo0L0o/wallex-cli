from argparse import Namespace
from typing import Any

from market.application.container import ApplicationContainer


def register(subparsers: Any) -> None:
    parser = subparsers.add_parser("sync", help="download markets and save them")
    parser.set_defaults(run_command=run)


async def run(args: Namespace, app: ApplicationContainer) -> int:
        count = await app.sync_markets.execute()
        print(f"Synced {count} markets.")
        return 0

