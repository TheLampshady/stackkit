"""Background jobs: one module per job, each with a ``main()``. See main.py."""

import json
import os
import re
from typing import Any

# A job is a module in jobs/: lowercase letters, digits and _
NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
# The variable a run's input arrives in, as a JSON object
PAYLOAD_VAR = "JOB_PAYLOAD"


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


def payload() -> dict[str, Any]:
    """
    The input this run was started with, such as ``{"db": "zach"}``.

    ``cli.py run --payload db=zach``, a timer's ``payload`` and an API call all
    set it. Locally, ``make run-job JOB=x ARGS="--payload db=zach"`` does too.

    :return: The input, empty when the run was given none
    :raises TypeError: If it isn't a JSON object
    """
    raw = os.environ.get(PAYLOAD_VAR, "")
    if not raw:
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise TypeError(f"{PAYLOAD_VAR} must be a JSON object")
    return data
