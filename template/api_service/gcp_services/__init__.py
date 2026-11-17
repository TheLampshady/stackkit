import logging
import os

from .gcp_logging import setup_logging

logger = logging.getLogger(__name__)

# Cloud Run services (and Agent Engine) set K_SERVICE; Cloud Run jobs set
# CLOUD_RUN_JOB instead
IS_CLOUD_RUN = bool(os.getenv("K_SERVICE") or os.getenv("CLOUD_RUN_JOB"))
IS_GAE = bool(os.getenv("GAE_INSTANCE") or os.getenv("GAE_ENV"))
IS_GCP = IS_GAE or IS_CLOUD_RUN or bool(os.getenv("IS_GCP"))

METADATA_PROJECT_ID_URL = (
    "http://metadata.google.internal/computeMetadata/v1/project/project-id"
)

# Setup logging for local vs GCP
setup_logging(is_local=not IS_GCP)


def fetch_metadata_project_id() -> str | None:
    """
    Reads the project ID from the GCP metadata server.

    :return: The project ID, or None when the metadata server is unreachable.
    :side effects: One HTTP request to the metadata server; logs on failure.
    """
    import urllib.request

    request = urllib.request.Request(
        METADATA_PROJECT_ID_URL, headers={"Metadata-Flavor": "Google"}
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.read().decode("utf-8").strip() or None
    except Exception:
        logger.warning("Could not read project ID from metadata server", exc_info=True)
        return None


# Cloud Run doesn't set GOOGLE_CLOUD_PROJECT, so pull it from the metadata server
if IS_CLOUD_RUN and not os.getenv("GOOGLE_CLOUD_PROJECT"):
    metadata_project_id = fetch_metadata_project_id()
    if metadata_project_id:
        os.environ["GOOGLE_CLOUD_PROJECT"] = metadata_project_id

# Everyone has issues with this.
logger.debug(f"IS_GCP: {IS_GCP}")
logger.debug(f"K_SERVICE: {os.getenv('K_SERVICE')}")
logger.debug(f"GAE_INSTANCE: {os.getenv('GAE_INSTANCE')}")
logger.debug(f"GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
