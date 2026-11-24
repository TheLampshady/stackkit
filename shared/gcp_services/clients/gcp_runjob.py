"""
Starts background jobs from the server and keeps track of them in Firestore.

The server's own endpoints call :func:`start_job`; users never start a job
directly. The job reports back through :func:`track_run`, which
``job_service/main.py`` calls for every run started this way. Each run is one
document in ``job_runs``:

- ``job``, ``key``, ``payload``, ``owner``: what was started, and for whom
- ``status``: ``queued``, ``running``, ``retrying``, ``done`` or ``failed``
- ``attempt``, ``error``, ``execution`` (the run's name at Google)
- ``created_at``, ``updated_at`` and ``deadline_at``

A run that is still ``queued``, ``running`` or ``retrying`` after
``deadline_at`` has stopped without reporting back (it ran out of time or
memory, or crashed): Cloud Run stops every run at its timeout. Treat it as
failed; :func:`get_run` does.

Each job's ``job_limits/<job>`` document lists the runs it has going, so
``start_job`` can refuse a second run with the same ``key``, and more than
``limit`` runs at once. Every start of that job changes the same document, so
Firestore lets them through one at a time however many server instances run.
When too many arrive at once to get through, ``start_job`` says busy (429).

Users can't read or write either collection: ``firestore.rules`` blocks every
client, and the server's Admin SDK isn't bound by those rules.

Locally (``USE_EMULATOR``), runs go to ``job_service/emulator.py``, which runs
them on this computer. ``make emulator`` starts it.
"""

import asyncio
import inspect
import json
import logging
import os
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import cache
from typing import Any

from app_settings import settings
from google.cloud.firestore import DELETE_FIELD, async_transactional

from .gcp_services import db

logger = logging.getLogger(__name__)

RUNS = "job_runs"
LIMITS = "job_limits"
# The variables a run gets; job_service/jobs/__init__.py reads the payload's
RUN_ID_VAR = "JOB_RUN_ID"
PAYLOAD_VAR = "JOB_PAYLOAD"
# Runs of one job that may go at once, unless start_job is told otherwise
DEFAULT_LIMIT = 10
# How long a run can take, every try included: its timeout times (retries + 1).
# job_service.toml's built-in values are 60m and 1 retry. Pass deadline= for a
# job with other values (the backfill example's 6h timeout needs 12 hours).
DEFAULT_DEADLINE = timedelta(hours=2)
# Where job_service/emulator.py listens
EMULATOR_HOST = os.environ.get("CLOUD_RUN_EMULATOR_HOST") or "127.0.0.1:8090"
# The emulator ignores the project, but the client needs one (gcp/.firebaserc's)
EMULATOR_PROJECT = "demo-dev"
# Saving a run's status: tries before giving up and only logging it
SAVE_TRIES = 3
UNFINISHED = ("queued", "running", "retrying")


class JobBusyError(Exception):
    """The job already has as many runs going as its limit allows."""


def cloud_run_name(job: str) -> str:
    """
    The job's name at Google, as ``job_service/cli.py`` deploys it.

    :param job: A module name in ``job_service/jobs/``, such as ``summarize_file``
    :return: ``<NAMESPACE>-<job>`` with dashes for underscores
    """
    name = f"{settings.namespace}-{job}" if settings.namespace else job
    return name.replace("_", "-")


def reserve(
    active: dict[str, dict[str, Any]],
    run_id: str,
    key: str | None,
    limit: int | None,
    now: datetime,
    deadline_at: datetime,
) -> tuple[dict[str, dict[str, Any]], str | None]:
    """
    Decide whether a new run may start, given the runs a job has going.

    :param active: The job's runs going, by run id, each with ``key`` and ``deadline_at``
    :param run_id: The new run's id
    :param key: Only one run with this key at a time; None for no check
    :param limit: Runs allowed at once; None for no limit
    :param now: The time now
    :param deadline_at: When the new run must be over
    :return: The runs going afterwards (past their deadline dropped), and the id
        of a run already going with the same key, if there is one
    :raises JobBusyError: If ``limit`` runs are already going
    """
    going = {rid: run for rid, run in active.items() if run["deadline_at"] > now}
    if key is not None:
        for rid, run in going.items():
            if run.get("key") == key:
                return going, rid
    if limit is not None and len(going) >= limit:
        raise JobBusyError(f"{len(going)} runs are already going (limit {limit})")
    going[run_id] = {"key": key, "deadline_at": deadline_at}
    return going, None


async def start_job(
    job: str,
    payload: dict[str, Any] | None = None,
    *,
    key: str | None = None,
    owner: str | None = None,
    limit: int | None = DEFAULT_LIMIT,
    deadline: timedelta = DEFAULT_DEADLINE,
) -> str:
    """
    Start a background job and return its run id at once; the job keeps going.

    Call it from the server's own endpoints, after checking the request.

    :param job: A module name in ``job_service/jobs/``, deployed with ``make deploy-job``
    :param payload: The run's input, which the job reads with ``jobs.payload()``
    :param key: Only one run with this key at a time, such as ``f"report:{uid}"``:
        while one is going, its id is returned instead of starting another
    :param owner: Who started it, such as the caller's email, so only they see it
    :param limit: Runs of this job allowed at once; None for no limit
    :param deadline: How long a run can take, every try included
    :return: The run's id, its document in ``job_runs``
    :raises JobBusyError: If ``limit`` runs are already going, or too many
        starts arrive at once (reply 429)
    :side effects: Writes to ``job_limits`` and ``job_runs``, and starts the job
        at Google (or in ``job_service/emulator.py`` locally)
    """
    now = datetime.now(UTC)
    run_id = uuid.uuid4().hex
    limits_ref = db.collection(LIMITS).document(job)
    run_ref = db.collection(RUNS).document(run_id)

    @async_transactional
    async def claim(transaction: Any) -> str | None:
        snapshot = await limits_ref.get(transaction=transaction)
        active = (snapshot.to_dict() or {}).get("active", {})
        going, existing = reserve(active, run_id, key, limit, now, now + deadline)
        if existing:
            return existing
        transaction.set(limits_ref, {"active": going})
        transaction.set(
            run_ref,
            {
                "job": job,
                "key": key,
                "payload": payload or {},
                "owner": owner,
                "status": "queued",
                "attempt": 0,
                "error": None,
                "execution": None,
                "created_at": now,
                "updated_at": now,
                "deadline_at": now + deadline,
            },
        )
        return None

    try:
        existing = await claim(db.transaction())
    except ValueError as error:  # Firestore gave up: too many starts at once
        raise JobBusyError(f"Too many starts of {job} at once") from error
    if existing:
        logger.info("Run %s of %s is already going for %s", existing, job, key)
        return existing
    try:
        execution = await asyncio.to_thread(run_at_google, job, run_id, payload or {})
    except Exception as error:
        await finish_run(job, run_id, "failed", error=f"Couldn't start: {error}")
        raise
    # The job is going: a failed save here mustn't make the caller start another
    try:
        await run_ref.update({"execution": execution})
    except Exception:
        logger.exception("Couldn't save run %s's execution name", run_id)
    logger.info("Started %s as run %s (%s)", job, run_id, execution)
    return run_id


@cache
def jobs_client() -> Any:
    """
    The Cloud Run client: Google's, or ``job_service/emulator.py`` locally.

    :return: A ``run_v2.JobsClient``
    """
    from google.cloud import run_v2

    if settings.use_emulator:
        from google.api_core.client_options import ClientOptions
        from google.auth.credentials import AnonymousCredentials

        return run_v2.JobsClient(
            transport="rest",
            credentials=AnonymousCredentials(),
            client_options=ClientOptions(api_endpoint=f"http://{EMULATOR_HOST}"),
        )
    return run_v2.JobsClient()


def run_at_google(job: str, run_id: str, payload: dict[str, Any]) -> str:
    """
    Ask Cloud Run to run the job once, with the run id and payload.

    :param job: A module name in ``job_service/jobs/``
    :param run_id: The run's id, for the job to report back to
    :param payload: The run's input
    :return: The execution's name at Google
    :raises google.api_core.exceptions.GoogleAPICallError: If Cloud Run refused,
        such as when the job isn't deployed
    :side effects: Starts a Cloud Run job execution
    """
    from google.cloud import run_v2

    region = os.environ.get("REGION") or "us-central1"
    project = settings.project_id
    if settings.use_emulator:
        project = project or EMULATOR_PROJECT
    parent = f"projects/{project}/locations/{region}"
    name = f"{parent}/jobs/{cloud_run_name(job)}"
    env = [
        run_v2.EnvVar(name=RUN_ID_VAR, value=run_id),
        run_v2.EnvVar(name=PAYLOAD_VAR, value=json.dumps(payload)),
    ]
    request = run_v2.RunJobRequest(
        name=name,
        overrides=run_v2.RunJobRequest.Overrides(
            container_overrides=[
                run_v2.RunJobRequest.Overrides.ContainerOverride(env=env)
            ]
        ),
    )
    operation = jobs_client().run_job(request=request)
    try:
        return operation.metadata.name
    except Exception:  # It started; the name is only for finding it in the console
        logger.exception("Started %s, but couldn't read its execution name", job)
        return ""


async def get_run(run_id: str) -> dict[str, Any] | None:
    """
    Read a run, marking it failed if it's past its deadline without finishing.

    :param run_id: The id ``start_job`` returned
    :return: The run's document, or None if there's no such run
    :side effects: Saves ``failed`` for a run past its deadline
    """
    snapshot = await db.collection(RUNS).document(run_id).get()
    if not snapshot.exists:
        return None
    run = snapshot.to_dict() or {}
    if run.get("status") in UNFINISHED and run["deadline_at"] <= datetime.now(UTC):
        error = (
            "Stopped without reporting back: it ran out of time or memory, or crashed"
        )
        await finish_run(run["job"], run_id, "failed", error=error)
        run |= {"status": "failed", "error": error}
    return run


async def finish_run(
    job: str, run_id: str, status: str, *, error: str | None = None
) -> None:
    """
    Save a run's final status and free its place in the job's limit.

    :param job: The job's module name
    :param run_id: The run's id
    :param status: ``done`` or ``failed``
    :param error: What went wrong, for ``failed``
    :side effects: Updates ``job_runs/<run_id>`` and ``job_limits/<job>``
    """
    batch = db.batch()
    batch.set(
        db.collection(RUNS).document(run_id),
        {"status": status, "error": error, "updated_at": datetime.now(UTC)},
        merge=True,
    )
    batch.set(
        db.collection(LIMITS).document(job),
        {"active": {run_id: DELETE_FIELD}},
        merge=True,
    )
    await batch.commit()


async def set_status(run_id: str, status: str, **fields: Any) -> None:
    """
    Save a run's status while it's still going.

    :param run_id: The run's id
    :param status: ``running`` or ``retrying``
    :param fields: Other fields to save, such as ``attempt`` or ``error``
    :side effects: Updates ``job_runs/<run_id>``
    """
    await (
        db.collection(RUNS)
        .document(run_id)
        .set({"status": status, "updated_at": datetime.now(UTC), **fields}, merge=True)
    )


async def save_quietly(save: Callable[[], Any], what: str) -> None:
    """
    Save a run's status, trying a few times, and only log it if that fails.

    Once the job's work is over, failing here would make Cloud Run run it again.

    :param save: Makes the save, such as ``lambda: finish_run(...)``
    :param what: What's being saved, for the log
    :side effects: Whatever ``save`` writes
    """
    for attempt in range(1, SAVE_TRIES + 1):
        try:
            await save()
            return
        except Exception:
            if attempt == SAVE_TRIES:
                logger.exception("Couldn't save %s", what)
                return
            await asyncio.sleep(attempt)


async def track_run(job: str, run_id: str, work: Callable[[], Any]) -> None:
    """
    Run a job's ``main()`` and report how it went to its ``job_runs`` document.

    ``job_service/main.py`` calls this for runs ``start_job`` started. A failed
    try that Cloud Run will try again is saved as ``retrying``; only the last
    one is ``failed``. Such jobs should run as one task (``tasks = 1``).

    :param job: The job's module name
    :param run_id: The run's id, from ``JOB_RUN_ID``
    :param work: The job's ``main``, plain or async
    :raises BaseException: Whatever the job raised, after saving it (an exit
        with code 0 counts as done)
    :side effects: Whatever the job does, and updates to ``job_runs`` and ``job_limits``
    """
    attempt = int(os.environ.get("CLOUD_RUN_TASK_ATTEMPT", "0"))
    retries = int(os.environ.get("MAX_RETRIES", "0"))
    await set_status(run_id, "running", attempt=attempt)
    try:
        # A plain main() runs on its own thread, so it may call asyncio.run itself
        result = await asyncio.to_thread(work)
        if inspect.isawaitable(result):
            await result
    except BaseException as error:
        if isinstance(error, SystemExit) and error.code in (0, None):
            await save_quietly(
                lambda: finish_run(job, run_id, "done"), f"run {run_id} done"
            )
            raise
        message = f"{type(error).__name__}: {error}"
        what = f"run {run_id}'s failure"
        if attempt < retries:
            await save_quietly(
                lambda: set_status(run_id, "retrying", error=message), what
            )
        else:
            await save_quietly(
                lambda: finish_run(job, run_id, "failed", error=message), what
            )
        raise
    await save_quietly(lambda: finish_run(job, run_id, "done"), f"run {run_id} done")
