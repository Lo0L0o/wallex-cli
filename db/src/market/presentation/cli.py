import argparse
from collections.abc import Sequence

from market.presentation.commands import register_commands


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="market-cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    register_commands(subparsers)
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return create_parser().parse_args(argv)

