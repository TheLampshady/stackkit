"""Smoke tests for agent import chains.

Verifies that agents can be imported and export root_agent.
This catches sys.path and import chain issues early.
"""

from unittest.mock import MagicMock, patch


@patch("gcp_services.clients.gcp_services.get_firebase_app", return_value=MagicMock())
@patch("gcp_services.clients.gcp_services.firestore_async")
@patch("gcp_services.gcp_secrets.load_secrets")
@patch("gcp_services.IS_GCP", False)
def test_agent1_exports_root_agent(mock_secrets, mock_firestore, mock_app):
    """agent1 should export root_agent."""
    from agents.agent1 import root_agent

    assert root_agent is not None
    assert root_agent.name == "ConversionAgent"


@patch("gcp_services.clients.gcp_services.get_firebase_app", return_value=MagicMock())
@patch("gcp_services.clients.gcp_services.firestore_async")
@patch("gcp_services.gcp_secrets.load_secrets")
@patch("gcp_services.IS_GCP", False)
def test_agent2_exports_root_agent(mock_secrets, mock_firestore, mock_app):
    """agent2 should export root_agent."""
    from agents.agent2 import root_agent

    assert root_agent is not None
    assert root_agent.name == "LayoutAgent"
