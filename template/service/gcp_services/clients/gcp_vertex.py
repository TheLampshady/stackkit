"""
Gemini and Claude through Vertex AI with application default credentials.

``vertex`` is the singleton every LLM call goes through. ``generate_structured``
is the one method in the repository that calls the model: it asks for JSON in
the shape of a Pydantic schema, measures the call, reads token usage, and maps
provider failures to :class:`ModelError`. A model id starting with ``claude-``
goes to Claude, any other to Gemini; both return the same reply. A call that
times out or finds the model busy is tried once more. Temperature, timeout,
token cap, and retry are constants here; the model id comes from
``settings.default_text_model`` unless a caller passes one.
"""

import asyncio
import json
import logging
import os
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx
from anthropic import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncAnthropicVertex,
    transform_schema,
)
from anthropic.types import Message, OutputConfigParam
from app_settings import settings
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

# Needed to use service account over API key
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")

# Vertex AI endpoint for both Gemini and Claude.
LOCATION = "global"
TEMPERATURE = 0.2
# A batch runs inside one request and Cloud Run allows 900 seconds (docs/CLOUD.md).
# Two waves of steps, each call timing out twice, must fit: 2 * 2 * 180 < 900.
TIMEOUT_MS = 180_000
# 529 is Claude's "overloaded"; Gemini never sends it.
RETRY_CODES = frozenset({429, 503, 504, 529})
RETRY_DELAY_S = 2.0
# Claude requires a reply cap; a full step of activities with notes stays well under it.
CLAUDE_MAX_TOKENS = 32_000


def is_claude(model_id: str) -> bool:
    """
    Whether a model id names a Claude model.

    :param model_id: Model id.
    :return: True for ``claude-`` ids.
    """
    return model_id.startswith("claude-")


class ModelError(Exception):
    """The model call did not produce a JSON reply: provider error, timeout, or bad text."""


@dataclass(frozen=True)
class StructuredReply:
    """One structured model reply.

    ``parsed`` is the schema instance when the reply validated, else None; the
    caller re-validates ``raw_json`` to report the exact problem.
    """

    parsed: Any
    raw_json: dict[str, Any]
    input_tokens: int
    output_tokens: int
    latency_ms: int
    model: str


class VertexClient:
    """Manages the Gemini and Claude clients on Vertex AI.

    Each client is created on first access, not at import time.
    """

    def __init__(self) -> None:
        self._client: genai.Client | None = None
        self._claude: AsyncAnthropicVertex | None = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(
                vertexai=True,
                project=settings.project_id,
                location=LOCATION,
            )
        return self._client

    @property
    def claude(self) -> AsyncAnthropicVertex:
        if self._claude is None:
            # Our own one retry below; the SDK's would break the batch time budget.
            self._claude = AsyncAnthropicVertex(
                region=LOCATION,
                project_id=settings.project_id,
                timeout=TIMEOUT_MS / 1000,
                max_retries=0,
            )
        return self._claude

    async def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        *,
        model: str | None = None,
    ) -> StructuredReply:
        """
        Calls the model and requires a JSON reply in the shape of ``schema``.

        :param prompt: The rendered prompt.
        :param schema: Pydantic class used as the response schema and to parse the reply.
        :param model: Model id; defaults to ``settings.default_text_model``.
        :return: The reply with token counts and latency.
        :raises ModelError: Provider error, timeout, empty or non-JSON text.
        :side effects: One model call, two when the first times out or finds the
            model busy; one log line.
        """
        model_id = model or settings.default_text_model
        started = time.perf_counter()
        if is_claude(model_id):
            text, input_tokens, output_tokens = await self._claude_text(
                model_id, prompt, schema
            )
        else:
            text, input_tokens, output_tokens = await self._gemini_text(
                model_id, prompt, schema
            )
        latency_ms = int((time.perf_counter() - started) * 1000)
        if not text:
            raise ModelError("model returned no text")
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ModelError(f"model returned invalid JSON: {exc.msg}") from exc
        if not isinstance(raw, dict):
            raise ModelError("model returned JSON that is not an object")
        try:
            parsed: Any = schema.model_validate(raw)
        except ValidationError:
            parsed = None
        logger.info(
            "model=%s latency_ms=%s tokens=%s/%s parsed=%s",
            model_id,
            latency_ms,
            input_tokens,
            output_tokens,
            parsed is not None,
        )
        return StructuredReply(
            parsed=parsed,
            raw_json=raw,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            model=model_id,
        )

    async def _gemini_text(
        self, model_id: str, prompt: str, schema: type[BaseModel]
    ) -> tuple[str | None, int, int]:
        """
        Calls Gemini with the schema as its response schema.

        :param model_id: Model id.
        :param prompt: The rendered prompt.
        :param schema: Pydantic class used as the response schema.
        :return: ``(text, input_tokens, output_tokens)``; thinking counts as output.
        :raises ModelError: Any provider error or timeout, after the retry.
        :side effects: One or two model calls.
        """
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=TEMPERATURE,
            http_options=types.HttpOptions(timeout=TIMEOUT_MS),
        )
        response: types.GenerateContentResponse = await self._call(
            model_id,
            lambda: self.client.aio.models.generate_content(
                model=model_id, contents=prompt, config=config
            ),
        )
        usage = response.usage_metadata
        input_tokens = int((usage.prompt_token_count or 0) if usage else 0)
        output_tokens = int(
            ((usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0))
            if usage
            else 0
        )
        return response.text, input_tokens, output_tokens

    async def _claude_text(
        self, model_id: str, prompt: str, schema: type[BaseModel]
    ) -> tuple[str | None, int, int]:
        """
        Calls Claude with the schema as its structured output format.

        Claude takes no temperature, so ``TEMPERATURE`` applies to Gemini only.

        :param model_id: Model id.
        :param prompt: The rendered prompt.
        :param schema: Pydantic class converted to Claude's JSON schema subset.
        :return: ``(text, input_tokens, output_tokens)``.
        :raises ModelError: Any provider error or timeout after the retry, a
            refusal, or a reply cut off at ``CLAUDE_MAX_TOKENS``.
        :side effects: One or two model calls.
        """
        output_config: OutputConfigParam = {
            "format": {"type": "json_schema", "schema": transform_schema(schema)}
        }
        response: Message = await self._call(
            model_id,
            lambda: self.claude.messages.create(
                model=model_id,
                max_tokens=CLAUDE_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
                output_config=output_config,
            ),
        )
        if response.stop_reason == "max_tokens":
            raise ModelError(f"model reply was cut off at {CLAUDE_MAX_TOKENS} tokens")
        if response.stop_reason == "refusal":
            raise ModelError("model refused the request")
        text = "".join(b.text for b in response.content if b.type == "text")
        usage = response.usage
        return text, int(usage.input_tokens or 0), int(usage.output_tokens or 0)

    async def _call(self, model_id: str, send: Callable[[], Awaitable[Any]]) -> Any:
        """
        Calls the model, trying once more after a timeout or a busy reply.

        :param model_id: Model id, for the retry warning.
        :param send: Makes one provider call.
        :return: The provider response.
        :raises ModelError: Any provider error or timeout, after the retry when
            one applies.
        :side effects: One or two model calls; a warning before a retry.
        """
        for attempt in (1, 2):
            try:
                return await send()
            except Exception as exc:
                code, timed_out = _failure(exc)
                if timed_out:
                    if attempt == 2:
                        raise ModelError("model call timed out") from exc
                    reason = "timeout"
                elif code is None:
                    raise
                elif attempt == 2 or code not in RETRY_CODES:
                    message = getattr(exc, "message", None) or exc
                    raise ModelError(f"model call failed: {code} {message}") from exc
                else:
                    reason = str(code)
            logger.warning("model=%s retrying after %s", model_id, reason)
            await asyncio.sleep(RETRY_DELAY_S)
        raise AssertionError("unreachable")


def _failure(exc: Exception) -> tuple[int | None, bool]:
    """
    Reads a provider exception as a status code or a timeout.

    :param exc: The exception a model call raised.
    :return: ``(status_code, timed_out)``; ``(None, False)`` when it is not a
        provider failure, so the caller re-raises it.
    """
    if isinstance(exc, (TimeoutError, httpx.TimeoutException, APITimeoutError)):
        return None, True
    if isinstance(exc, errors.APIError):
        return exc.code, False
    if isinstance(exc, APIStatusError):
        return exc.status_code, False
    if isinstance(exc, APIConnectionError):
        return 0, False
    return None, False


vertex = VertexClient()
