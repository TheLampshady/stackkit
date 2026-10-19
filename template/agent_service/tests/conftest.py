"""
Test fixtures for agent_service tests.

Provides mocked GCP services so tests can run without network access.
"""

import sys
from os import path

# Add agent_service/ to sys.path so imports resolve to agent_service's
# copies (not service's). Must happen before any agent_service imports.
_agent_service_dir = path.dirname(path.dirname(path.abspath(__file__)))
if _agent_service_dir not in sys.path:
    sys.path.insert(0, _agent_service_dir)

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_firebase_app():
    """Mock Firebase app initialization."""
    with patch("gcp_services.clients.gcp_services.get_firebase_app") as mock_app:
        mock_app.return_value = MagicMock()
        yield mock_app


@pytest.fixture
def mock_firestore_db():
    """Mock Firestore async client."""
    with patch("gcp_services.clients.gcp_services.db") as mock_db:
        mock_db.collection = MagicMock(return_value=MagicMock())
        mock_db.collection.return_value.document = MagicMock(return_value=MagicMock())
        mock_db.collection.return_value.document.return_value.get = AsyncMock()
        yield mock_db


@pytest.fixture
def mock_gcp_services(mock_firebase_app, mock_firestore_db):
    """Combined fixture for all mocked GCP services."""
    return {
        "app": mock_firebase_app,
        "db": mock_firestore_db,
    }
