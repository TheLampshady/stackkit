"""
Configures settings for agent service.

The settings every service has are in `gcp_services/base_settings.py`.
Add what only the agents need.

Loads settings from
 - `.env` for local instances
 - env variables from GCP environment for deployed instances
"""

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

    # Custom variables


settings = Settings()
