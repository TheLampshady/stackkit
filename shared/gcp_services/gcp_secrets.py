"""
Pulls variables with GCP secret manager.

*NOTE*: Only sets variables that aren't set.

Requires local auth.

Ex: name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/{version_id}"

"""

import logging
import os

from google.auth import default as default_auth
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

SECRET_PATH = "projects/{0}/secrets/{1}/versions/latest"


def load_secrets(keys: list[str], project: str | None = None) -> None:
    """
    Loads secrets from the GCP secret manager and sets them as environment variables.

    Fails silently to allow for local execution without GCP credentials.
    If no project is provided, it attempts to get the default project from the
    environment's credentials.

    :param keys: A list of secret key names to load.
    :param project: The GCP project ID.
    """
    project = project or _get_default_project()
    if not project:
        return

    for key_name in keys:
        try:
            client = secretmanager.SecretManagerServiceClient()
            secret_path = SECRET_PATH.format(project, key_name)
            resp = client.access_secret_version(name=secret_path)
            data = resp.payload.data
            if data:
                decoded = data.decode("utf-8")
                os.environ.setdefault(key_name, decoded)
            logger.info(f"GCP Secrets: {key_name} loaded.")
        except Exception as e:  # noqa: BLE001 - best-effort load, any failure just leaves the env var unset
            logger.warning(f"GCP Secrets: {key_name} not loaded: {e}")


def _get_default_project() -> str | None:
    """
    Gets the default GCP project ID from the environment's credentials.

    :return: The GCP project ID, or None if it cannot be determined.
    """
    project = None
    try:
        _, project = default_auth()
    except DefaultCredentialsError:
        pass
    return project
