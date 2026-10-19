"""
Configures settings for project usage.

Loads settings from
 - `.env` for local instances
 - env variables from GCP environment for deployed instances

Initializes GCP variables as well
"""

import os
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from gcp_services import IS_CLOUD_RUN, IS_GAE, IS_GCP
from gcp_services.gcp_secrets import load_secrets
from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

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
# Set here so every genai.Client (service code and ADK agents) resolves to Vertex.
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

    # LLM: model id for vertex.generate_structured when a caller passes none.
    # A "claude-" id goes to Claude, any other to Gemini.
    default_text_model: str = os.environ.get("DEFAULT_TEXT_MODEL") or "gemini-3.8-flash"

    static_dir: Path = app_dir / "static"

    # Local Frontend Hosting Controls
    front_end_url: str = os.environ.get("FRONT_END_URL", "").strip("/")

    # Custom variables
    # - Don't use emulator if env has false or
    use_emulator: bool = env_var_as_bool("USE_EMULATOR", not IS_GCP)

    # TODO feel free to hard code a name
    namespace: str | None = os.environ.get("NAMESPACE") or None
    firestore_db_name: str | None = os.environ.get("FIRESTORE_DB_NAME") or namespace

    firestore_bucket_name: str | None = os.environ.get("FIRESTORE_BUCKET_NAME") or (
        f"{project_id}-{namespace}" if namespace else None
    )

    # Auth: email domains allowed through fb_auth and iap_auth.
    # Blank (VALID_DOMAINS=) disables the domain check and allows any account.
    valid_domains: Annotated[list[str], NoDecode] = []

    # Auth (IAP): explicit audience wins; otherwise derived on Cloud Run
    iap_audience: str | None = os.environ.get("IAP_AUDIENCE") or None
    cloud_run_service: str | None = os.environ.get("K_SERVICE") or None
    # Auth (IAP): local identity override, ignored on deployed instances
    local_user_email: str | None = (
        os.environ.get("LOCAL_USER_EMAIL") or "test@gmail.com"
    )

    @field_validator("valid_domains", mode="before")
    @classmethod
    def split_domains(cls, value: str | list[str]) -> list[str]:
        """
        Reads VALID_DOMAINS as a comma-separated string rather than JSON.

        :param value: Raw env value or list
        :return: Lowercased domains, blanks dropped
        """
        if isinstance(value, str):
            value = value.split(",")
        return [d.strip().lower() for d in value if d.strip()]


settings = Settings()
