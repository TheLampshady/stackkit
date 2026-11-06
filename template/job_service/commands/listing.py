"""``list`` and ``runs``: what's online, on a timer, and running."""

from typing import Annotated, Any

import typer

from commands.common import (
    gcloud_json,
    get_state,
    job_id,
    known_jobs,
    pick_jobs,
    require_project,
)


def short(name: str) -> str:
    """
    The last part of a Google resource path.

    :param name: Such as ``projects/p/locations/l/jobs/nightly``
    :return: Such as ``nightly``
    """
    return name.rsplit("/", 1)[-1]


def execution_state(item: dict[str, Any]) -> str:
    """
    Say where a Cloud Run job execution is.

    :param item: One execution from ``gcloud run jobs executions list``
    :return: running, failed, succeeded or pending
    """
    status = item.get("status", {})
    if status.get("completionTime"):
        return "failed" if status.get("failedCount") else "succeeded"
    return "running" if status.get("runningCount") else "pending"


def list_jobs(ctx: typer.Context) -> None:
    """Show each job in jobs/, whether it's online, and its timers."""
    state = get_state(ctx)
    require_project(state)
    online = {
        short(item.get("metadata", {}).get("name", ""))
        for item in gcloud_json(
            [
                "run",
                "jobs",
                "list",
                f"--project={state.project_id}",
                f"--region={state.region}",
            ]
        )
    }
    timers = gcloud_json(
        [
            "scheduler",
            "jobs",
            "list",
            f"--project={state.project_id}",
            f"--location={state.region}",
        ]
    )
    rows = []
    for job in known_jobs():
        gid = job_id(state.namespace, job)
        own = [
            f"{short(t['name'])} ({t.get('schedule', '?')}"
            f"{', paused' if t.get('state') == 'PAUSED' else ''})"
            for t in timers
            if f"/jobs/{gid}:run" in t.get("httpTarget", {}).get("uri", "")
        ]
        rows.append((job, "yes" if gid in online else "no", ", ".join(own) or "-"))
    width = max([len(r[0]) for r in rows] + [3])
    typer.echo(f"{'JOB':<{width}}  ONLINE  TIMERS")
    for job, there, own in rows:
        typer.echo(f"{job:<{width}}  {there:<6}  {own}")


def runs(
    ctx: typer.Context,
    job: Annotated[str | None, typer.Argument(help="One job. Default: all.")] = None,
    active: Annotated[
        bool, typer.Option("--active", help="Only runs happening now.")
    ] = False,
    limit: Annotated[int, typer.Option(help="Most recent runs per job.")] = 10,
) -> None:
    """Show recent runs, newest first, or with --active the ones in progress."""
    state = get_state(ctx)
    require_project(state)
    names = pick_jobs(job, job is None)
    shown = 0
    for name in names:
        items = gcloud_json(
            [
                "run", "jobs", "executions", "list",
                f"--job={job_id(state.namespace, name)}",
                f"--project={state.project_id}",
                f"--region={state.region}",
                f"--limit={limit}",
            ]
        )  # fmt: skip
        for item in items:
            current = execution_state(item)
            if active and current != "running":
                continue
            started = item.get("status", {}).get("startTime", "-")
            typer.echo(
                f"{name}  {short(item.get('metadata', {}).get('name', '?'))}  {current}  {started}"
            )
            shown += 1
    if not shown:
        typer.echo("Nothing running." if active else "No runs yet.")
