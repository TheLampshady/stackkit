"""
Initializes the firebase app for cloud and local development.

This is used for the firestore and auth services.
"""

from app_settings import settings
from firebase_admin import auth, firestore_async

from .fb_config import get_firebase_app
from .gcp_storage import get_firebase_bucket

# Directory with local firebase configs
firebase_dir = settings.root_dir / "gcp"
project_id = settings.project_id if settings.is_local else None
app = get_firebase_app(settings.use_emulator, firebase_dir, project_id)

# Initialize Firestore
database_id = settings.firestore_db_name if not settings.use_emulator else None
db = firestore_async.client(app, database_id=database_id)

# Initialize Auth client
auth_client = auth.Client(app)

# Initialize Cloud Storage bucket
bucket = get_firebase_bucket(app, settings.firestore_bucket_name)
