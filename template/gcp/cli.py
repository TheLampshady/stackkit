#!/usr/bin/env python3
"""Root CLI for GCP tooling.

Run from anywhere in the repo::

    uv run gcp/cli.py --help
    uv run gcp/cli.py split-cookie https://your-app.appspot.com/
    uv run gcp/cli.py provision

Environment variables are loaded from the project root ``.env`` before any command
runs, so commands can fall back to ``PROJECT_ID``, ``NAMESPACE``, etc.
"""

import sys
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv

# Allow `uv run gcp/cli.py` and `python -m gcp.cli` to resolve `commands.*` alike.
sys.path.insert(0, str(Path(__file__).resolve().parent))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"

# `provision` reads settings from the service package; make it importable too.
sys.path.insert(0, str(PROJECT_ROOT / "service"))

from commands.provision import provision
from commands.split_cookie import split_cookie

app = typer.Typer(
    help="GCP tooling for this project.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def main(
    env_file: Annotated[
        Path,
        typer.Option(
            "--env-file",
            help="Env file to load. Defaults to the project root .env",
            show_default=False,
        ),
    ] = DEFAULT_ENV_FILE,
) -> None:
    """Load environment variables before dispatching to a command.

    :param env_file: Path to the env file to load
    :side effects: Populates ``os.environ`` from the env file (existing vars win)
    """
    load_dotenv(env_file, override=False)


app.command("provision")(provision)
app.command("split-cookie")(split_cookie)


if __name__ == "__main__":
    app()
