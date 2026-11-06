"""``schedule`` and ``unschedule``: Google timers that start a job."""

from typing import Annotated

import typer

from commands.common import (
    DEFAULT_TIME_ZONE,
    LABEL_RE,
    DryRun,
    JsonOption,
    PayloadOption,
    State,
    Timer,
    build_payload,
    gcloud,
    get_state,
    job_id,
    pick_jobs,
    require_project,
    run_body,
    succeeded,
    timer_id,
    timers_for,
)


def apply_timer(state: State, timer: Timer, number: str, dry_run: bool) -> None:
    """
    Create the timer at Google, or update it when it's already there.

    :param state: The shared settings
    :param timer: The timer to set
    :param number: The project number, for the account that starts the job
    :param dry_run: Print instead of running
    :side effects: Creates or changes a Cloud Scheduler job
    """
    name = timer_id(state.namespace, timer)
    where = [f"--project={state.project_id}", f"--location={state.region}"]
    action = "create"
    if not dry_run:
        found = gcloud(
            ["scheduler", "jobs", "describe", name, *where],
            changes=False,
            capture=True,
        )
        action = "update" if found.returncode == 0 else "create"
    uri = (
        f"https://run.googleapis.com/v2/projects/{state.project_id}"
        f"/locations/{state.region}/jobs/{job_id(state.namespace, timer.job)}:run"
    )
    args = [
        "scheduler", "jobs", action, "http", name, *where,
        f"--schedule={timer.cron}",
        f"--time-zone={timer.time_zone}",
        f"--uri={uri}",
        "--http-method=POST",
        f"--oauth-service-account-email={number}-compute@developer.gserviceaccount.com",
        "--headers=Content-Type=application/json",
        # Always sent, so removing a payload from a timer also clears the old one
        f"--message-body={run_body(timer.payload)}",
        "--quiet",
    ]  # fmt: skip
    succeeded(gcloud(args, dry_run=dry_run))


def schedule(
    ctx: typer.Context,
    job: Annotated[str | None, typer.Argument(help="A job in jobs/.")] = None,
    all_jobs: Annotated[
        bool, typer.Option("--all", help="Every timer in job_service.toml.")
    ] = False,
    cron: Annotated[
        str | None, typer.Option(help='When to run, as cron: "0 6 * * *".')
    ] = None,
    name: Annotated[
        str | None,
        typer.Option(help="Tells this timer apart from the job's others."),
    ] = None,
    tz: Annotated[
        str | None,
        typer.Option(help=f"Time zone for the cron. Default {DEFAULT_TIME_ZONE}."),
    ] = None,
    payload: PayloadOption = None,
    json_file: JsonOption = None,
    dry_run: DryRun = False,
) -> None:
    """
    Run a job on a timer. Run again with the same name to change it.

    With --cron it sets one timer from the flags. Without it, it sets the timers
    listed for the job (or every job, with --all) in job_service.toml.
    """
    state = get_state(ctx)
    require_project(state)
    names = pick_jobs(job, all_jobs)
    if cron:
        if all_jobs:
            raise typer.BadParameter(
                "--cron sets one timer; name a job instead of --all."
            )
        if name is not None and not LABEL_RE.match(name):
            raise typer.BadParameter("Use lowercase letters, digits, - and _.")
        timers = [
            Timer(
                job=names[0],
                name=name,
                cron=cron,
                time_zone=tz or DEFAULT_TIME_ZONE,
                payload=build_payload(payload, json_file),
            )
        ]
    else:
        if payload or json_file or name or tz:
            raise typer.BadParameter("--payload, --json, --name and --tz need --cron.")
        timers = [t for n in names for t in timers_for(state.config, n)]
        if not timers:
            raise typer.BadParameter(
                "No timers in job_service.toml for that. Pass --cron to make one."
            )

    # Google's timer starts the job as the Compute Engine default account
    number = "PROJECT_NUMBER"
    if not dry_run:
        found = gcloud(
            [
                "projects", "describe", state.project_id,
                "--format=value(projectNumber)",
            ],
            changes=False,
            capture=True,
        )  # fmt: skip
        succeeded(found)
        number = found.stdout.strip()
    for timer in timers:
        apply_timer(state, timer, number, dry_run)


def unschedule(
    ctx: typer.Context,
    job: Annotated[str, typer.Argument(help="A job in jobs/.")],
    name: Annotated[
        str | None, typer.Option(help="The timer's name, if it has one.")
    ] = None,
    dry_run: DryRun = False,
) -> None:
    """Remove a job's timer. The job stays and can still be started by hand."""
    state = get_state(ctx)
    require_project(state)
    pick_jobs(job, False)
    timer = Timer(job=job, name=name, cron="", time_zone="", payload={})
    succeeded(
        gcloud(
            [
                "scheduler",
                "jobs",
                "delete",
                timer_id(state.namespace, timer),
                f"--project={state.project_id}",
                f"--location={state.region}",
                "--quiet",
            ],
            dry_run=dry_run,
        )
    )
