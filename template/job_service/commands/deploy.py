"""``deploy``: put jobs online at Google, without starting them."""

import subprocess
from typing import Annotated

import typer

from commands.common import (
    JOB_DIR,
    DryRun,
    deploy_settings,
    gcloud,
    get_state,
    job_id,
    pick_jobs,
    require_project,
    succeeded,
)


def deploy(
    ctx: typer.Context,
    job: Annotated[str | None, typer.Argument(help="A job in jobs/.")] = None,
    all_jobs: Annotated[
        bool, typer.Option("--all", help="Every job in jobs/.")
    ] = False,
    timeout: Annotated[
        str | None,
        typer.Option(help="Stop a run after this long, such as 90m. 24h at most."),
    ] = None,
    retries: Annotated[
        int | None, typer.Option(help="Tries again when a run fails.")
    ] = None,
    tasks: Annotated[
        int | None, typer.Option(help="Copies of the job to run at once.")
    ] = None,
    cpu: Annotated[str | None, typer.Option(help="CPUs per task, such as 2.")] = None,
    memory: Annotated[
        str | None, typer.Option(help="Memory per task, such as 2Gi.")
    ] = None,
    dry_run: DryRun = False,
) -> None:
    """
    Build the job folder at Google and create or update the job. It doesn't run.

    Settings come from these flags, then ``[jobs.<job>]`` and ``[defaults]`` in
    job_service.toml, then built-in values.
    \f
    :param ctx: The command's Typer context
    :param job: The job to deploy
    :param all_jobs: Deploy every job in ``jobs/`` instead
    :param timeout: How long a run may take
    :param retries: Tries again when a run fails
    :param tasks: Copies of the job that run at once
    :param cpu: CPUs per task
    :param memory: Memory per task
    :param dry_run: Print the commands instead of running them
    :raises typer.Exit: If the build or gcloud failed
    :side effects: Runs ``make build``, then creates or updates Cloud Run jobs
    """
    state = get_state(ctx)
    require_project(state)
    names = pick_jobs(job, all_jobs)

    # Copies the shared clients in and writes requirements.txt
    build = ["make", "-C", str(JOB_DIR), "build"]
    typer.echo("+ " + " ".join(build))
    if not dry_run and subprocess.run(build, check=False).returncode != 0:
        raise typer.Exit(1)

    flags = {
        "timeout": timeout,
        "retries": retries,
        "tasks": tasks,
        "cpu": cpu,
        "memory": memory,
    }
    for name in names:
        settings = deploy_settings(state.config, name)
        settings.update({k: v for k, v in flags.items() if v is not None})
        env = f"JOB_NAME={name}"
        if state.namespace:
            env += f",NAMESPACE={state.namespace}"
        args = [
            "run", "jobs", "deploy", job_id(state.namespace, name),
            "--source=.",
            f"--project={state.project_id}",
            f"--region={state.region}",
            f"--tasks={settings['tasks']}",
            f"--max-retries={settings['retries']}",
            f"--task-timeout={settings['timeout']}",
            f"--set-env-vars={env}",
            "--quiet",
        ]  # fmt: skip
        for option in ("cpu", "memory"):
            if settings.get(option):
                args.append(f"--{option}={settings[option]}")
        succeeded(gcloud(args, dry_run=dry_run))
