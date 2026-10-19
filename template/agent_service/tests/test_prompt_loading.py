"""Tests for dynamic prompt loading from Firestore."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_db():
    """Mock Firestore db for prompt tests."""
    with patch("gcp_services.clients.gcp_services.db") as db:
        yield db


@pytest.mark.asyncio
async def test_get_instruction_returns_firestore_prompt(mock_db):
    """When Firestore doc exists with instruction, return it."""
    doc_mock = MagicMock()
    doc_mock.exists = True
    doc_mock.to_dict.return_value = {"instruction": "Custom prompt from Firestore"}

    mock_db.collection.return_value.document.return_value.get = AsyncMock(
        return_value=doc_mock
    )

    from agents.agent1.prompt import get_instruction

    result = await get_instruction(MagicMock())
    assert result == "Custom prompt from Firestore"


@pytest.mark.asyncio
async def test_get_instruction_returns_default_when_doc_missing(mock_db):
    """When Firestore doc doesn't exist, return default instruction."""
    doc_mock = MagicMock()
    doc_mock.exists = False

    mock_db.collection.return_value.document.return_value.get = AsyncMock(
        return_value=doc_mock
    )

    from agents.agent1.prompt import DEFAULT_INSTRUCTION, get_instruction

    result = await get_instruction(MagicMock())
    assert result == DEFAULT_INSTRUCTION


@pytest.mark.asyncio
async def test_get_instruction_returns_default_on_error():
    """When Firestore access fails, return default instruction."""
    with patch(
        "gcp_services.clients.gcp_services.db",
        new_callable=lambda: MagicMock(side_effect=Exception("Connection failed")),
    ):
        from agents.agent1.prompt import DEFAULT_INSTRUCTION, get_instruction

        result = await get_instruction(MagicMock())
        assert result == DEFAULT_INSTRUCTION
