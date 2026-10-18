import asyncio
import logging
import sys
from collections.abc import Sequence

from market.application.container import ApplicationContainer
from market.config import Settings
from market.presentation.cli import parse_args


async def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)
    app: ApplicationContainer | None = None
    try:
        app = ApplicationContainer(Settings.from_environment())
        return await args.run_command(args, app)
    except Exception as error:
        logging.error("Command failed: %s", error)
        return 1
    finally:
        if app is not None:
            await app.close()


def cli() -> int:
    return asyncio.run(main())


if __name__ == "__main__":
    sys.exit(cli())
