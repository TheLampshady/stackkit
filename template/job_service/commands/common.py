"""Pieces the job commands share: settings, names, payloads and running gcloud."""

import json
import re
import shlex
import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, cast

import typer
from jobs import NAME_RE, PAYLOAD_VAR

JOB_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = JOB_DIR / "job_service.toml"
LABEL_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
# What Cloud Run takes as a job name
CLOUD_RUN_NAME_RE = re.compile(r"^[a-z]([-a-z0-9]{0,61}[a-z0-9])?$")
# What a job gets when neither a flag nor job_service.toml says otherwise
BUILT_IN: dict[str, Any] = {"timeout": "60m", "retries": 1, "tasks": 1}
DEFAULT_REGION = "us-central1"
DEFAULT_TIME_ZONE = "Etc/UTC"

DryRun = Annotated[
    bool,
    typer.Option("--dry-run", help="Print the gcloud commands without running them."),
]
PayloadOption = Annotated[
    list[str] | None,
    typer.Option(
        "--payload", "-p", help="Input for the job as key=value. Repeat for more."
    ),
]
JsonOption = Annotated[
    Path | None,
    typer.Option(
        "--json",
        help="A JSON file holding the job's input. --payload keys win over it.",
        exists=True,
        dir_okay=False,
    ),
]


@dataclass
class State:
    """What every command needs, set once by the CLI's callback."""

    project_id: str
    namespace: str
    region: str
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Timer:
    """One Google timer that starts a job, maybe with its own input."""

    job: str
    name: str | None
    cron: str
    time_zone: str
    payload: dict[str, Any]


def get_state(ctx: typer.Context) -> State:
    """
    Get the settings the CLI's callback stored.

    :param ctx: The command's Typer context
    :return: The shared settings
    """
    return cast(State, ctx.obj)


def require_project(state: State) -> None:
    """
    Stop with a clear message when no project is set.

    :param state: The shared settings
    :raises typer.BadParameter: If there is no project id
    """
    if not state.project_id:
        raise typer.BadParameter("Set PROJECT_ID in .env, or pass --project-id.")


def load_config(path: Path = CONFIG_FILE) -> dict[str, Any]:
    """
    Read ``job_service.toml``.

    :param path: The file to read
    :return: Its contents, or an empty dict when the file isn't there
    """
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle)


def known_jobs() -> list[str]:
    """
    List the jobs in ``jobs/``.

    :return: Module names, sorted
    """
    folder = JOB_DIR / "jobs"
    return sorted(p.stem for p in folder.glob("*.py") if NAME_RE.match(p.stem))


def pick_jobs(job: str | None, every: bool) -> list[str]:
    """
    Turn "one job or --all" into the list of job names to act on.

    :param job: The job named on the command line, if any
    :param every: Whether --all was passed
    :return: Job names
    :raises typer.BadParameter: If both or neither were given, or the job is unknown
    """
    if every and job is None:
        return known_jobs()
    if every or job is None:
        raise typer.BadParameter("Name one job, or pass --all.")
    if job not in known_jobs():
        raise typer.BadParameter(
            f"No job {job!r} in jobs/. Jobs here: {', '.join(known_jobs()) or 'none'}"
        )
    return [job]


def job_id(namespace: str, job: str) -> str:
    """
    The job's name at Google: ``<NAMESPACE>-<job>`` with dashes for underscores.

    :param namespace: The project's NAMESPACE, or blank
    :param job: A module name in ``jobs/``
    :return: The Cloud Run job name
    :raises typer.BadParameter: If Cloud Run won't take the name, such as an
        uppercase NAMESPACE
    """
    name = (f"{namespace}-{job}" if namespace else job).replace("_", "-")
    if not CLOUD_RUN_NAME_RE.match(name):
        raise typer.BadParameter(
            f"{name!r} can't be a Cloud Run job name: NAMESPACE and the job's name "
            "must be lowercase letters, digits and -, 63 characters at most."
        )
    return name


def timer_id(namespace: str, timer: Timer) -> str:
    """
    The timer's name at Google: the job's name, plus ``_<name>`` when it has one.

    The job's name has no ``_``, so the first one marks where the timer's name
    starts: job ``a`` with timer ``b`` and job ``a_b`` can't get the same id.

    :param namespace: The project's NAMESPACE, or blank
    :param timer: The timer
    :return: The Cloud Scheduler job name
    """
    base = job_id(namespace, timer.job)
    return f"{base}_{timer.name}" if timer.name else base


def deploy_settings(config: dict[str, Any], job: str) -> dict[str, Any]:
    """
    Merge the built-in values, ``[defaults]`` and ``[jobs.<job>]``, latest wins.

    :param config: The parsed ``job_service.toml``
    :param job: A job name
    :return: Settings such as timeout, retries, tasks, cpu and memory
    """
    own = dict(config.get("jobs", {}).get(job, {}))
    own.pop("schedules", None)
    return {**BUILT_IN, **config.get("defaults", {}), **own}


def timers_for(config: dict[str, Any], job: str) -> list[Timer]:
    """
    Read a job's timers from ``[[jobs.<job>.schedules]]``.

    :param config: The parsed ``job_service.toml``
    :param job: A job name
    :return: Its timers, none when it has none
    :raises typer.BadParameter: If a timer has no cron or a bad name
    """
    timers = []
    for entry in config.get("jobs", {}).get(job, {}).get("schedules", []):
        if not entry.get("cron"):
            raise typer.BadParameter(
                f"A timer for {job} in job_service.toml has no cron."
            )
        name = entry.get("name")
        if name is not None and not LABEL_RE.match(name):
            raise typer.BadParameter(
                f"Timer name {name!r}: lowercase letters, digits, - and _."
            )
        timers.append(
            Timer(
                job=job,
                name=name,
                cron=entry["cron"],
                time_zone=entry.get("time_zone", DEFAULT_TIME_ZONE),
                payload=dict(entry.get("payload", {})),
            )
        )
    return timers


def build_payload(pairs: list[str] | None, json_file: Path | None) -> dict[str, Any]:
    """
    Combine a JSON file and ``key=value`` pairs into the job's input.

    :param pairs: Values from ``--payload``
    :param json_file: A file from ``--json``
    :return: The input, ``--payload`` keys winning over the file
    :raises typer.BadParameter: If the file isn't a JSON object or a pair has no ``=``
    """
    data: dict[str, Any] = {}
    if json_file is not None:
        try:
            loaded = json.loads(json_file.read_text())
        except json.JSONDecodeError as error:
            raise typer.BadParameter(
                f"{json_file} isn't valid JSON: {error}"
            ) from error
        if not isinstance(loaded, dict):
            raise typer.BadParameter(
                f"{json_file} must hold a JSON object, like {{...}}"
            )
        data.update(loaded)
    for pair in pairs or []:
        key, separator, value = pair.partition("=")
        if not separator or not key:
            raise typer.BadParameter(f"{pair!r}: write it as key=value")
        data[key] = value
    return data


def env_flag(name: str, value: str) -> str:
    """
    Build gcloud's ``--update-env-vars`` argument, safe for commas in the value.

    gcloud splits on commas, which JSON has, so the value is wrapped in a
    delimiter that doesn't appear in it (gcloud's ``^X^`` syntax).

    :param name: The variable name
    :param value: Its value
    :return: The flag, such as ``--update-env-vars=^@^JOB_PAYLOAD={...}``
    """
    delimiter = next(c for c in "@#~|;!" if c not in value)
    return f"--update-env-vars=^{delimiter}^{name}={value}"


def run_body(payload: dict[str, Any]) -> str:
    """
    The request body that makes a Cloud Run job run with the payload.

    :param payload: The job's input, may be empty
    :return: JSON for the Cloud Run ``:run`` call
    """
    if not payload:
        return "{}"
    env = [{"name": PAYLOAD_VAR, "value": json.dumps(payload)}]
    return json.dumps({"overrides": {"containerOverrides": [{"env": env}]}})


def gcloud(
    args: list[str],
    *,
    dry_run: bool = False,
    changes: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    """
    Run gcloud from the job folder.

    Commands that change something are printed first. With ``dry_run`` they are
    printed and not run; read-only ones (``changes=False``) always run.

    :param args: Everything after ``gcloud``
    :param dry_run: Print instead of running a command that changes something
    :param changes: False for a read-only command
    :param capture: Collect output instead of showing it
    :return: The finished process
    :raises typer.Exit: If gcloud isn't installed
    :side effects: Runs gcloud, which may create or change things at Google
    """
    command = ["gcloud", *args]
    if changes:
        typer.echo("+ " + shlex.join(command))
        if dry_run:
            return subprocess.CompletedProcess(command, 0, "", "")
    try:
        return subprocess.run(
            command, cwd=JOB_DIR, text=True, capture_output=capture, check=False
        )
    except FileNotFoundError:
        typer.echo("gcloud isn't installed. See docs/ENVIRONMENTS.md.", err=True)
        raise typer.Exit(1) from None


def succeeded(result: subprocess.CompletedProcess[str]) -> None:
    """
    Stop with gcloud's exit code when it failed.

    :param result: A finished gcloud call
    :raises typer.Exit: If it failed
    """
    if result.returncode != 0:
        if result.stderr:
            typer.echo(result.stderr, err=True)
        raise typer.Exit(result.returncode)


def gcloud_json(args: list[str]) -> list[dict[str, Any]]:
    """
    Run a read-only gcloud list command and parse its JSON.

    :param args: Everything after ``gcloud``, without ``--format``
    :return: The items it listed
    :raises typer.Exit: If gcloud failed
    """
    result = gcloud([*args, "--format=json"], changes=False, capture=True)
    succeeded(result)
    return json.loads(result.stdout or "[]")
