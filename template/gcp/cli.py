#!/usr/bin/env python3
"""Root CLI for GCP tooling.

Run from anywhere in the repo::

    uv run gcp/cli.py --help
stackkit:begin gae
    uv run gcp/cli.py split-cookie https://your-app.appspot.com/
stackkit:end gae
stackkit:begin firebase
    uv run gcp/cli.py provision
stackkit:end firebase

The project root ``.env`` (or ``--env-file``) is loaded before any command runs
and wins over variables already set, so commands read ``PROJECT_ID``,
``NAMESPACE``, etc. from it.
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

# stackkit:begin firebase
from commands.provision import provision

# stackkit:end firebase
# stackkit:begin gae
from commands.split_cookie import split_cookie

# stackkit:end gae

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
    :raises typer.BadParameter: When ``--env-file`` names a file that is not there
    :side effects: Populates ``os.environ`` from the env file (the file wins over
        variables already set, like the services' settings)
    """
    if env_file != DEFAULT_ENV_FILE and not env_file.exists():
        raise typer.BadParameter(f"{env_file} not found", param_hint="--env-file")
    load_dotenv(env_file, override=True)


# stackkit:begin firebase
app.command("provision")(provision)
# stackkit:end firebase
# stackkit:begin gae
app.command("split-cookie")(split_cookie)
# stackkit:end gae


if __name__ == "__main__":
    app()
