"""
Prompt management for ConversionAgent.

Loads instruction from Firestore if available, falls back to default.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from google.adk.agents.readonly_context import ReadonlyContext

DEFAULT_INSTRUCTION = "Answer questions"

PROMPTS_COLLECTION = "prompts"
AGENT_NAME = "ConversionAgent"

brief_for_recommendation = """
Here is the brief that should be used to recommend the components:

{brief}
"""


async def get_instruction(ctx: ReadonlyContext) -> str:
    """
    Load agent instruction from Firestore, falling back to default.

    Reads from Firestore collection `prompts/{agent_name}`.
    Returns the `instruction` field if the document exists,
    otherwise returns DEFAULT_INSTRUCTION.

    :return: The agent instruction string.
    """
    try:
        from gcp_services.clients.gcp_services import db

        doc_ref = db.collection(PROMPTS_COLLECTION).document(AGENT_NAME)
        doc = await doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            instruction: str | None = data.get("instruction") if data else None
            if instruction:
                logger.info(f"Loaded prompt from Firestore for {AGENT_NAME}")
                return instruction
    except Exception:
        logger.warning(
            f"Failed to load prompt from Firestore for {AGENT_NAME}, using default",
            exc_info=True,
        )

    return DEFAULT_INSTRUCTION
