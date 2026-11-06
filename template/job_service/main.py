"""
Runs one background job, then exits.

Each job is a module in ``jobs/`` with a ``main()`` function, plain or async.
Locally: ``make run-job JOB=example``. On Cloud Run every job deploys from this
folder, and ``JOB_NAME`` (set by ``make deploy-job``) says which one to run.

Usage::

    python main.py example
    JOB_NAME=example python main.py
"""

import asyncio
import importlib
import inspect
import logging
import os
import sys

import app_settings  # noqa: F401  (loads .env and sets up logging first)
from jobs import NAME_RE

logger = logging.getLogger(__name__)


def run(name: str) -> None:
    """
    Run the job named ``name`` to completion.

    :param name: A module name in ``jobs/``, such as ``example``
    :raises ValueError: If the name isn't a valid job module name
    :raises ModuleNotFoundError: If there is no such job
    :side effects: Whatever the job does
    """
    if not NAME_RE.match(name):
        raise ValueError(f"Job names are lowercase letters, digits and _: {name!r}")
    job = importlib.import_module(f"jobs.{name}")
    logger.info("Starting job %s", name)
    result = job.main()
    if inspect.isawaitable(result):
        asyncio.run(result)
    logger.info("Finished job %s", name)


if __name__ == "__main__":
    job_name = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("JOB_NAME")
    if not job_name:
        sys.exit("Say which job to run: python main.py <name>, or set JOB_NAME")
    run(job_name)
