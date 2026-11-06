"""
Settings every service shares.

Each service's ``app_settings.py`` loads its environment with
``load_environment`` and subclasses ``CoreSettings`` to add what only that
service needs. Each service has its own copy of ``gcp_services/``, so a change
every service needs goes in each copy.

Loads settings from
 - `.env` for local instances
 - env variables from GCP environment for deployed instances

Defaults that read the environment are factories, so they run when a
``Settings()`` is created, after ``load_environment`` and the secrets are in.
"""

import os
from pathlib import Path
from typing import Annotated, Self

from dotenv import load_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from . import IS_CLOUD_RUN, IS_GAE, IS_GCP


def find_dotenv_file(app_dir: Path, filename: str = ".env") -> Path | None:
    """
    Finds the env file. It checks in order
    - Working directory
    - The service's own directory
    - Parent of the service's directory

    :param app_dir: The service's directory (where its ``app_settings.py`` is).
    :param filename: The name of the env file to find.
    :return: The path to the env file, or None if not found.
    """
    for folder in (Path.cwd(), app_dir, app_dir.parent):
        env_path = folder / filename
        if env_path.exists():
            return env_path
    return None


def load_environment(app_dir: Path) -> Path | None:
    """
    Loads ``.env`` into the environment and sets the GCP variables.

    Call it once, before the secrets are loaded and ``Settings()`` is created.

    :param app_dir: The service's directory (where its ``app_settings.py`` is).
    :return: The env file that was loaded, or None if there is none.
    :side effects: Sets GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION (and the
        Vertex flag when the ai module is kept) in ``os.environ``.
    """
    env_file = find_dotenv_file(app_dir)
    load_dotenv(env_file, override=True)

    # Project target. Check .env file then environ
    project_id = (
        os.environ.get("PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT") or ""
    )
    # Overwrite GOOGLE_CLOUD_PROJECT in case local has this var set for Gemini code assist
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
    os.environ.setdefault(
        "GOOGLE_CLOUD_LOCATION",
        os.environ.get("GOOGLE_CLOUD_LOCATION") or "us-central1",
    )

    # stackkit:begin ai
    # LLM calls use Vertex AI with ADC / the runtime service account, never an API key.
    # Set here so every genai.Client (service code and ADK agents) resolves to Vertex.
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
    # stackkit:end ai
    return env_file


def env_var_as_bool(var_name: str, default: bool) -> bool:
    """
    Converts an environment variable to a boolean.

    :param var_name: The name of the environment variable.
    :param default: The default value to use if the environment variable is not set.
    :return: The boolean value of the environment variable.
    """
    value = os.environ.get(var_name, default)
    return str(value).lower() not in ("0", "false", "no", "", None)


class CoreSettings(BaseSettings):
    """The settings every service has. A service subclasses it in ``app_settings.py``."""

    model_config = SettingsConfigDict(extra="allow", env_file_encoding="utf-8")

    # Where the service lives and which env file it loaded: each service sets these
    app_dir: Path
    root_dir: Path
    env_file: Path | None = None
    current_dir: Path = Field(default_factory=Path.cwd)

    is_local: bool = not IS_GCP
    is_gcp: bool = IS_GCP
    is_gae: bool = IS_GAE
    is_cloud_run: bool = IS_CLOUD_RUN

    project_id: str = Field(
        default_factory=lambda: os.environ.get("GOOGLE_CLOUD_PROJECT") or ""
    )
    location: str = Field(
        default_factory=lambda: os.environ.get("GOOGLE_CLOUD_LOCATION") or "us-central1"
    )

    # stackkit:begin ai
    # LLM: model id for vertex.generate_structured when a caller passes none.
    # A "claude-" id goes to Claude, any other to Gemini.
    default_text_model: str = Field(
        default_factory=lambda: (
            os.environ.get("DEFAULT_TEXT_MODEL") or "gemini-3.8-flash"
        )
    )
    # stackkit:end ai

    # stackkit:begin firebase
    # Firebase emulator: on locally, off on GCP, unless USE_EMULATOR says otherwise
    use_emulator: bool = Field(
        default_factory=lambda: env_var_as_bool("USE_EMULATOR", not IS_GCP)
    )
    # stackkit:end firebase

    # TODO feel free to hard code a name
    namespace: str | None = Field(
        default_factory=lambda: os.environ.get("NAMESPACE") or None
    )
    # stackkit:begin database
    firestore_db_name: str | None = Field(
        default_factory=lambda: os.environ.get("FIRESTORE_DB_NAME") or None
    )
    # stackkit:end database
    # stackkit:begin storage
    firestore_bucket_name: str | None = Field(
        default_factory=lambda: os.environ.get("FIRESTORE_BUCKET_NAME") or None
    )
    # stackkit:end storage

    # stackkit:begin auth_iap,auth_firebase
    # Auth: email domains allowed to sign in.
    # Blank (VALID_DOMAINS=) disables the domain check and allows any account.
    valid_domains: Annotated[list[str], NoDecode] = []
    # stackkit:end auth_iap,auth_firebase
    # stackkit:begin auth_iap
    # Auth (IAP): explicit audience wins; otherwise derived on Cloud Run
    iap_audience: str | None = Field(
        default_factory=lambda: os.environ.get("IAP_AUDIENCE") or None
    )
    cloud_run_service: str | None = Field(
        default_factory=lambda: os.environ.get("K_SERVICE") or None
    )
    # Auth (IAP): local identity override, ignored on deployed instances
    local_user_email: str | None = Field(
        default_factory=lambda: os.environ.get("LOCAL_USER_EMAIL") or "test@gmail.com"
    )
    # stackkit:end auth_iap

    # stackkit:begin auth_iap,auth_firebase
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

    # stackkit:end auth_iap,auth_firebase
    # stackkit:begin database
    @model_validator(mode="after")
    def default_db_name(self) -> Self:
        """
        Names the Firestore database after the namespace unless one is set.

        :return: The settings
        """
        self.firestore_db_name = self.firestore_db_name or self.namespace
        return self

    # stackkit:end database
    # stackkit:begin storage
    @model_validator(mode="after")
    def default_bucket_name(self) -> Self:
        """
        Names the Storage bucket ``{project_id}-{namespace}`` unless one is set.

        :return: The settings
        """
        if not self.firestore_bucket_name and self.namespace:
            self.firestore_bucket_name = f"{self.project_id}-{self.namespace}"
        return self

    # stackkit:end storage
