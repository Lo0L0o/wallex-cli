from pathlib import Path

from alembic import command
from alembic.config import Config


def migrate() -> None:
    config_path = Path.cwd() / "alembic.ini"
    if not config_path.is_file():
        raise SystemExit("Run this command in the project folder containing alembic.ini")
    command.upgrade(Config(str(config_path)), "head")
    print("Database migrations applied.")
