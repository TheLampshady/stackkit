"""``run``: start a job once, at Google or on this computer."""

import json
import os
import subprocess
import sys
from typing import Annotated

import typer

from commands.common import (
    JOB_DIR,
    PAYLOAD_VAR,
    DryRun,
    JsonOption,
    PayloadOption,
    build_payload,
    env_flag,
    gcloud,
    get_state,
    job_id,
    pick_jobs,
    require_project,
    succeeded,
)


def run(
    ctx: typer.Context,
    job: Annotated[str, typer.Argument(help="A job in jobs/.")],
    local: Annotated[
        bool,
        typer.Option(
            "--local/--remote",
            help="Run on this computer, or at Google (the default).",
        ),
    ] = False,
    payload: PayloadOption = None,
    json_file: JsonOption = None,
    wait: Annotated[
        bool, typer.Option(help="At Google: wait until it finishes.")
    ] = False,
    dry_run: DryRun = False,
) -> None:
    """
    Run a job once. The job reads its input with ``jobs.payload()``.

    Remote runs need the job deployed first (``deploy``).
    """
    state = get_state(ctx)
    pick_jobs(job, False)
    data = build_payload(payload, json_file)
    text = json.dumps(data) if data else ""

    if local:
        env = {**os.environ}
        if text:
            env[PAYLOAD_VAR] = text
        command = [sys.executable, "main.py", job]
        typer.echo(
            f"+ {PAYLOAD_VAR}={text!r} " + " ".join(command)
            if text
            else "+ " + " ".join(command)
        )
        if dry_run:
            return
        code = subprocess.run(command, cwd=JOB_DIR, env=env, check=False).returncode
        raise typer.Exit(code)

    require_project(state)
    args = [
        "run", "jobs", "execute", job_id(state.namespace, job),
        f"--project={state.project_id}",
        f"--region={state.region}",
    ]  # fmt: skip
    if text:
        args.append(env_flag(PAYLOAD_VAR, text))
    if wait:
        args.append("--wait")
    succeeded(gcloud(args, dry_run=dry_run))
