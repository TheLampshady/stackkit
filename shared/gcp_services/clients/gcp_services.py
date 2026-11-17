"""
Initializes the firebase app for cloud and local development, and the
clients this project uses from it.
"""

from app_settings import settings
from firebase_admin import auth, firestore_async

from .fb_config import get_firebase_app

# stackkit:begin storage
from .gcp_storage import get_firebase_bucket

# stackkit:end storage
# Directory with local firebase configs
firebase_dir = settings.root_dir / "gcp"
project_id = settings.project_id if settings.is_local else None
app = get_firebase_app(settings.use_emulator, firebase_dir, project_id)

# stackkit:begin database
# Initialize Firestore
database_id = settings.firestore_db_name if not settings.use_emulator else None
db = firestore_async.client(app, database_id=database_id)
# stackkit:end database
# stackkit:begin auth_firebase
# Initialize Auth client
auth_client = auth.Client(app)
# stackkit:end auth_firebase
# stackkit:begin storage
# Initialize Cloud Storage bucket
bucket = get_firebase_bucket(app, settings.firestore_bucket_name)
# stackkit:end storage
