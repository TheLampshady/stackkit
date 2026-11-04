"""
Configures settings for the background jobs.

Loads settings from
 - `.env` for local instances
 - env variables from GCP environment for deployed instances

Initializes GCP variables as well
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from gcp_services import IS_CLOUD_RUN, IS_GAE, IS_GCP
from gcp_services.gcp_secrets import load_secrets
from pydantic_settings import BaseSettings, SettingsConfigDict

# ------- Local ENV --------
# Loads the local .env file from project folder into settings

app_dir = Path(__file__).parent
root_dir = app_dir.parent
current_dir = Path.cwd()


def find_dotenv_file(filename: str = ".env") -> Path | None:
    """
    Finds the env file. It checks in order
    - Working directory
    - Current settings directory
    - Parent of settings directory

    :param filename: The name of the env file to find.
    :return: The path to the env file, or None if not found.
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

    return None


env_file = find_dotenv_file()

# Loads the env file into the environment
load_dotenv(env_file, override=True)


# ------- GCP Variables --------
## Project target. Check .env file then environ
project_id = (
    os.environ.get("PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT") or ""
)

# Overwrite GOOGLE_CLOUD_PROJECT incase local has this var set for Gemini code assist
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION") or "us-central1"
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", GOOGLE_CLOUD_LOCATION)

# LLM calls use Vertex AI with ADC / the runtime service account, never an API key.
# Set here so every genai.Client resolves to Vertex.
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")

# ----------- Set Env with GCP Secrets -----------

# Loads envs from GCP secret manager into the ENV
if IS_GCP:
    SECRET_KEY_NAMES = ["TODO"]
    load_secrets(SECRET_KEY_NAMES)


# ----- Base Settings for Project --------


def env_var_as_bool(var_name: str, default: bool) -> bool:
    """
    Converts an environment variable to a boolean.

    :param var_name: The name of the environment variable.
    :param default: The default value to use if the environment variable is not set.
    :return: The boolean value of the environment variable.
    """
    value = os.environ.get(var_name, default)
    return str(value).lower() not in ("0", "false", "no", "", None)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_file, extra="allow", env_file_encoding="utf-8"
    )

    current_dir: Path = current_dir
    app_dir: Path = app_dir
    root_dir: Path = root_dir
    env_file: Path | None = env_file
    is_local: bool = not IS_GCP
    is_gcp: bool = IS_GCP
    is_gae: bool = IS_GAE
    is_cloud_run: bool = IS_CLOUD_RUN

    project_id: str = project_id
    location: str = GOOGLE_CLOUD_LOCATION

    # stackkit:begin ai
    # LLM: model id for vertex.generate_structured when a caller passes none.
    # A "claude-" id goes to Claude, any other to Gemini.
    default_text_model: str = os.environ.get("DEFAULT_TEXT_MODEL") or "gemini-3.8-flash"

    # stackkit:end ai
    # stackkit:begin firebase
    # Firebase emulator: on locally, off on GCP, unless USE_EMULATOR says otherwise
    use_emulator: bool = env_var_as_bool("USE_EMULATOR", not IS_GCP)

    # stackkit:end firebase
    # TODO feel free to hard code a name
    namespace: str | None = os.environ.get("NAMESPACE") or None
    # stackkit:begin database
    firestore_db_name: str | None = os.environ.get("FIRESTORE_DB_NAME") or namespace
    # stackkit:end database
    # stackkit:begin storage
    firestore_bucket_name: str | None = os.environ.get("FIRESTORE_BUCKET_NAME") or (
        f"{project_id}-{namespace}" if namespace else None
    )
    # stackkit:end storage


settings = Settings()
