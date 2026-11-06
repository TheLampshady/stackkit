"""
Configures settings for project usage.

The settings every service shares are in `gcp_services/base_settings.py`
(edit `shared/gcp_services/base_settings.py`). This adds what only the API needs.

Loads settings from
 - `.env` for local instances
 - env variables from GCP environment for deployed instances
"""

import os
from pathlib import Path

from gcp_services import IS_GCP
from gcp_services.base_settings import CoreSettings, load_environment
from gcp_services.gcp_secrets import load_secrets
from pydantic_settings import SettingsConfigDict

app_dir = Path(__file__).parent
root_dir = app_dir.parent

# Loads the local .env file and sets the GCP variables
env_file = load_environment(app_dir)

# ----------- Set Env with GCP Secrets -----------

# Loads envs from GCP secret manager into the ENV
if IS_GCP:
    SECRET_KEY_NAMES = ["TODO"]
    load_secrets(SECRET_KEY_NAMES)


class Settings(CoreSettings):
    model_config = SettingsConfigDict(env_file=env_file)

    app_dir: Path = app_dir
    root_dir: Path = root_dir
    env_file: Path | None = env_file

    static_dir: Path = app_dir / "static"

    # Local Frontend Hosting Controls
    front_end_url: str = os.environ.get("FRONT_END_URL", "").strip("/")


settings = Settings()
