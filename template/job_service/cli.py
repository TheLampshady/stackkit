#!/usr/bin/env python3
"""Put background jobs online, run them and put them on a timer.

Run from this folder (``make`` does it for you)::

    uv run --package job_service --group cli python cli.py --help
    ... cli.py list
    ... cli.py deploy nightly
    ... cli.py schedule nightly --cron "0 6 * * *" --tz Europe/London --payload db=zach
    ... cli.py run nightly --payload db=zach            # at Google
    ... cli.py run nightly --local --payload db=zach    # on this computer
    ... cli.py runs --active

Per-job settings and timers live in ``job_service.toml``. The project root
``.env`` is loaded first, so commands fall back to ``PROJECT_ID`` and
``NAMESPACE``.
"""

import os
import sys
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))

from commands.common import DEFAULT_REGION, State, load_config
from commands.deploy import deploy
from commands.listing import list_jobs, runs
from commands.run import run
from commands.schedule import schedule, unschedule

DEFAULT_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

app = typer.Typer(
    help="Put background jobs online, run them and put them on a timer.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def main(
    ctx: typer.Context,
    env_file: Annotated[
        Path,
        typer.Option("--env-file", help="Env file to load.", show_default=False),
    ] = DEFAULT_ENV_FILE,
    project_id: Annotated[
        str | None,
        typer.Option("--project-id", help="Google project. Beats PROJECT_ID in .env."),
    ] = None,
    region: Annotated[
        str | None,
        typer.Option(help="Where the jobs live. Beats REGION in .env."),
    ] = None,
) -> None:
    """
    Load the env file and settings before dispatching to a command.

    :param ctx: The Typer context; its ``obj`` carries the settings
    :param env_file: Path to the env file to load
    :param project_id: Overrides ``PROJECT_ID`` from the environment
    :param region: Overrides the region from the toml and the environment
    :side effects: Populates ``os.environ`` from the env file (existing vars win)
    """
    load_dotenv(env_file, override=False)
    config = load_config()
    ctx.obj = State(
        project_id=project_id or os.environ.get("PROJECT_ID", ""),
        namespace=os.environ.get("NAMESPACE", ""),
        region=region or os.environ.get("REGION") or DEFAULT_REGION,
        config=config,
    )


app.command("deploy")(deploy)
app.command("schedule")(schedule)
app.command("unschedule")(unschedule)
app.command("run")(run)
app.command("list")(list_jobs)
app.command("runs")(runs)


if __name__ == "__main__":
    app()
