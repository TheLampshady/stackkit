"""``list`` and ``runs``: what's online, on a timer, and running."""

from typing import Annotated, Any

import typer

from commands.common import (
    State,
    gcloud_json,
    get_state,
    job_id,
    known_jobs,
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
    :return: running, cancelled, failed, succeeded or pending
    """
    status = item.get("status", {})
    if status.get("completionTime"):
        if status.get("cancelledCount"):
            return "cancelled"
        return "failed" if status.get("failedCount") else "succeeded"
    return "running" if status.get("runningCount") else "pending"


def online_ids(state: State) -> set[str]:
    """
    The names of the Cloud Run jobs in the project and region.

    :param state: The shared settings
    :return: Job names at Google, such as ``shop-example``
    :raises typer.Exit: If gcloud failed
    """
    return {
        short(item.get("metadata", {}).get("name", ""))
        for item in gcloud_json(
            [
                "run", "jobs", "list",
                f"--project={state.project_id}",
                f"--region={state.region}",
            ]
        )
    }  # fmt: skip


def job_rows(
    jobs: list[str], namespace: str, online: set[str], timers: list[dict[str, Any]]
) -> list[tuple[str, str, str]]:
    """
    One row per job: its name, whether it's online, and its timers.

    :param jobs: Job names in ``jobs/``
    :param namespace: The project's NAMESPACE, or blank
    :param online: Job names at Google, from ``online_ids``
    :param timers: Items from ``gcloud scheduler jobs list``
    :return: ``(job, "yes" or "no", timers or "-")`` for each job
    """
    rows = []
    for job in jobs:
        gid = job_id(namespace, job)
        own = [
            f"{short(t['name'])} ({t.get('schedule', '?')}"
            f"{', paused' if t.get('state') == 'PAUSED' else ''})"
            for t in timers
            if f"/jobs/{gid}:run" in t.get("httpTarget", {}).get("uri", "")
        ]
        rows.append((job, "yes" if gid in online else "no", ", ".join(own) or "-"))
    return rows


def runs_to_list(
    job: str | None, jobs: list[str], namespace: str, online: set[str]
) -> list[str]:
    """
    The jobs to show runs for: the one named, else every one that's online.

    :param job: The job named on the command line, if any
    :param jobs: Job names in ``jobs/``
    :param namespace: The project's NAMESPACE, or blank
    :param online: Job names at Google, from ``online_ids``
    :return: Job names
    :raises typer.BadParameter: If the named job isn't in ``jobs/`` or isn't online
    """
    if job is None:
        return [j for j in jobs if job_id(namespace, j) in online]
    if job not in jobs:
        raise typer.BadParameter(f"No job {job!r} in jobs/.")
    if job_id(namespace, job) not in online:
        raise typer.BadParameter(f"{job} isn't online. Deploy it first.")
    return [job]


def list_jobs(ctx: typer.Context) -> None:
    """
    Show each job in jobs/, whether it's online, and its timers.
    \f
    :param ctx: The command's Typer context
    """
    state = get_state(ctx)
    require_project(state)
    timers = gcloud_json(
        [
            "scheduler", "jobs", "list",
            f"--project={state.project_id}",
            f"--location={state.region}",
        ]
    )  # fmt: skip
    rows = job_rows(known_jobs(), state.namespace, online_ids(state), timers)
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
    """
    Show recent runs, newest first, or with --active the ones in progress.

    With no job it shows every job that's online.
    \f
    :param ctx: The command's Typer context
    :param job: One job, or None for every online job
    :param active: Only show runs in progress
    :param limit: The most recent runs to show per job
    """
    state = get_state(ctx)
    require_project(state)
    names = runs_to_list(job, known_jobs(), state.namespace, online_ids(state))
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
