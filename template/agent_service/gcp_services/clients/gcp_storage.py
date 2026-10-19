import logging

from app_settings import settings
from firebase_admin import App, storage
from google.cloud.storage.bucket import Bucket

logger = logging.getLogger(__name__)


def get_firebase_bucket(
    app: App,
    bucket_name: str | None = None,
) -> Bucket:
    """
    Returns the configured Firebase Storage bucket for the given app.

    :param app: The Firebase app instance to bind the bucket to.
    :param bucket_name: Optional bucket name override.
    :return: The configured Firebase Storage bucket.
    """

    if settings.use_emulator:
        bucket_name = None
    else:
        default_bucket = f"{settings.project_id}.firebasestorage.app"
        bucket_name = bucket_name or default_bucket

    bucket = storage.bucket(name=bucket_name, app=app)

    bucket_url = "https://firebasestorage.googleapis.com"

    if settings.use_emulator:
        bucket_url = bucket.client._connection.API_BASE_URL
    logger.info(f"DEFAULT BUCKET URL: {bucket_url}")
    return bucket
