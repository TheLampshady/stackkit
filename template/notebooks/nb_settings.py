"""
Configures settings for project usage.

Loads settings from
 - `.env` for local instances
 - env variables from GCP environment for deployed instances

Initializes GCP variables as well
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# ------- Local ENV --------
# Loads the local .env file from project folder into settings

app_dir = Path(__file__).parent
root_dir = app_dir.parent
current_dir = Path.cwd()


def find_dotenv_file(filename: str = ".env"):
    """
    Finds the env file. It checks in order
    - Working directory
    - Current settings directory
    - Parent of settings directory
    """

    env_path = current_dir / filename
    if env_path.exists():
        return env_path

    env_path = app_dir / filename
    if env_path.exists():
        return env_path

    env_path = root_dir / filename
    if env_path.exists():
        return env_path


env_file = find_dotenv_file()


# ------- GCP Variables --------
IS_GAE = bool(os.getenv("GAE_INSTANCE") or os.getenv("GAE_ENV"))
IS_CLOUD_RUN = bool(os.getenv("K_SERVICE"))
IS_GCP = IS_GAE or IS_CLOUD_RUN

# Everyone has issues with this.
logger.debug(f"IS_GCP: {IS_GCP}")
logger.debug(f"K_SERVICE: {os.getenv('K_SERVICE')}")
logger.debug(f"GAE_INSTANCE: {os.getenv('GAE_INSTANCE')}")


# ----- Base Settings for Project --------


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_file, extra="allow", env_file_encoding="utf-8"
    )

    current_dir: Path = current_dir
    app_dir: Path = app_dir
    root_dir: Path = root_dir
    env_file: Path | None = env_file
    is_local: bool = not IS_GCP
    project_id: str = os.environ.get("PROJECT_ID", "")
    region: str = os.environ.get("REGION", "us-central1")
    llm_model_name: str = os.environ.get("LLM_MODEL_NAME", "gemini-2.5-flash-lite")


settings = Settings()

# Load to env as well
load_dotenv(settings.env_file)

# ------- GCP init -------

# Used for default GCP init services
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", settings.project_id)
