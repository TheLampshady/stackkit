"""
A job with no timer: start it by hand when you need it, with input.

``make start-job JOB=backfill ARGS="--payload db=main"`` runs it at Google;
``make run-job JOB=backfill ARGS="--payload db=main"`` runs it here. Its limits
(a long timeout, more memory) are in ``job_service.toml``.
"""

import logging

from jobs import payload

logger = logging.getLogger(__name__)


async def main() -> None:
    """
    Log the input this run was started with. Replace it with the real work.

    :side effects: Logs
    """
    logger.info("Backfill job started with input %s", payload())
