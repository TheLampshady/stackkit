"""
An example job. Copy this file to start a new one, then run it with
``make run-job JOB=<file name>``.

A job runs, does its work and exits: a nightly summary, a sync from another
website, AI reading a batch of documents. It can run for up to a day.
"""

import logging

from app_settings import settings

from jobs import task_share

logger = logging.getLogger(__name__)


async def main() -> None:
    """
    Log which task this is and, with a database, record the run.

    :side effects: Logs; with a database, adds a document to ``job_runs``
    """
    index, count = task_share()
    logger.info(
        "Example job: task %s of %s in project %s",
        index + 1,
        count,
        settings.project_id or "(not set)",
    )
    # stackkit:begin database
    from datetime import UTC, datetime

    from gcp_services.clients.gcp_services import db

    await db.collection("job_runs").add(
        {"job": "example", "task": index, "finished_at": datetime.now(UTC)}
    )
    # stackkit:end database
