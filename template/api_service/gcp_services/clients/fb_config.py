"""
Functions for loading the proper configuration for the firebase app emulator

This is used for the firestore and auth services.

** Storage **
Auth: https://firebase.google.com/docs/storage/admin/start?hl=en&authuser=0
Manage: https://cloud.google.com/storage/docs/uploads-downloads?authuser=0

The default (and free buck you create in console will be:
    `PROJECT_ID.firebasestorage.app`

"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from firebase_admin import App, initialize_app

logger = logging.getLogger(__name__)


def initialize_local_firebase(
    firebase_dir: Path | None,
) -> App:
    """
    Initializes the Firebase app for local development with the emulator suite.

    The settings are read from the local `.firebaserc` and `firebase.json` files.

    :param firebase_dir: The directory containing the Firebase configuration files.
    :return: The initialized Firebase app.
    """
    # This project ID must match the firebase rc project settings.
    # Firebase emulator has a lot of hidden databases

    local_settings = _get_local_firebase_setting(firebase_dir)
    project_id = local_settings.get("project_id")
    options = {"projectId": project_id}

    # ------- Emulator Settings ------
    # Requires env variables set for each host

    # Firestore
    if db_host := local_settings.get("firestore"):
        os.environ.setdefault("FIRESTORE_EMULATOR_HOST", db_host)

    # Firebase Auth
    if auth_host := local_settings.get("auth"):
        os.environ.setdefault("FIREBASE_AUTH_EMULATOR_HOST", auth_host)

    # Firebase Storage
    # NOTE: not supported in python yet
    if storage_host := local_settings.get("storage"):
        os.environ.setdefault("FIREBASE_STORAGE_EMULATOR_HOST", storage_host)
        os.environ.setdefault("STORAGE_EMULATOR_HOST", f"http://{storage_host}")
        options["storageBucket"] = f"{project_id}.appspot.com"

    return initialize_app(options=options)


def _get_local_firebase_setting(gcp_dir: Path | None = None) -> dict[str, str]:
    """
    Reads the Firebase settings from local files for emulator configuration.

    Reads `.firebaserc` and `firebase.json` to determine the host and port for
    the emulators and the project ID.

    :param gcp_dir: The directory containing the Firebase configuration files.
    :return: A dictionary of local host settings for the Firebase emulators and the project ID.
    """
    gcp_dir = gcp_dir or Path()
    fb_file = gcp_dir / "firebase.json"
    rc_file = gcp_dir / ".firebaserc"

    if not fb_file.is_file() or not rc_file.is_file():
        logger.warning(f"Firebase files not found: {fb_file} or {rc_file}")
        return {}

    with open(rc_file) as f:
        rc_config: dict[str, Any] = json.load(f)
    with open(fb_file) as f:
        fb_config: dict[str, Any] = json.load(f)

    # Loops through the emulators and gets the ports
    all_settings = {}
    emulator_settings = fb_config.get("emulators") or {}
    for key in emulator_settings:
        if isinstance(emulator_settings[key], dict):
            port = emulator_settings[key].get("port")
            if port:
                all_settings[key] = f"localhost:{port}"

    # Gets the project ID
    project_id = rc_config.get("projects", {}).get("default") or ""
    all_settings["project_id"] = project_id or os.environ.get(
        "GOOGLE_CLOUD_PROJECT", ""
    )
    return all_settings


def get_firebase_app(
    use_emulator: bool = False,
    firebase_dir: Path | None = None,
    project_id: str | None = None,
) -> App:
    """
    Gets the Firebase app, configured for either local or deployed environments.

    Can use the emulator for local development or connect to the remote GCP services.

    :param use_emulator: A boolean to toggle using the emulator.
    :param firebase_dir: The directory with the `.firebaserc` and `firebase.json` files.
    :param project_id: The GCP project ID to use.
    :return: The initialized Firebase app.
    """

    if use_emulator:
        logger.info("Firebase Setup: Emulator")
        return initialize_local_firebase(firebase_dir)

    logger.info("Firebase Setup: Remote")

    # For some reason, Agent Engine sets GCP project to an # and that breaks this.
    if project_id:
        options = {"projectId": project_id}
        return initialize_app(options=options)

    return initialize_app()
