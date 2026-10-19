"""
Initializes the firebase app for cloud and local development.

Agents use Firestore only -- no auth client or storage bucket.
"""

from app_settings import settings
from firebase_admin import firestore_async

from .fb_config import get_firebase_app

# Directory with local firebase configs
firebase_dir = settings.root_dir / "gcp"
project_id = settings.project_id if settings.is_local else None
app = get_firebase_app(settings.use_emulator, firebase_dir, project_id)

# Initialize Firestore
database_id = settings.firestore_db_name if not settings.use_emulator else None
db = firestore_async.client(app, database_id=database_id)
