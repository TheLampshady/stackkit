"""Background jobs: one module per job, each with a ``main()``. See main.py."""

import os


def task_share() -> tuple[int, int]:
    """
    Which share of the work this copy of the job should do.

    Cloud Run can run a job as several tasks at once (``--tasks``) and tells
    each one its number. Locally, set the same variables to try it out.

    :return: This task's index (from 0) and how many tasks there are
    """
    index = int(os.environ.get("CLOUD_RUN_TASK_INDEX", "0"))
    count = int(os.environ.get("CLOUD_RUN_TASK_COUNT", "1"))
    return index, count
