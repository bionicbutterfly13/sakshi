"""LLM client protocol + two implementations.

The agent's cognition depends on this protocol, not on any specific
vendor SDK. ``AnthropicLLMClient`` is the real adapter (prompt caching
wired); ``MockLLMClient`` returns deterministic canned answers so tests
do not need network or an API key.

Sakshi's core package still imports zero LLM SDKs — only this example
optionally imports ``anthropic`` and only when the real client is
constructed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class LLMAnswer:
    """One LLM response, including a self-reported confidence."""

    text: str
    confidence: float
    cache_hit: bool = False


@runtime_checkable
class LLMClient(Protocol):
    """The minimal LLM seam this example depends on."""

    async def complete(
        self, *, system: str, user: str, max_tokens: int = 512
    ) -> LLMAnswer: ...


@dataclass
class MockLLMClient:
    """Deterministic canned-answers client for tests and offline demos.

    Stores ``(answer_text, confidence)`` keyed by a prefix of the user
    prompt. Useful for pinning the agent's decision graph without
    making any network call.
    """

    canned: dict[str, tuple[str, float]]

    async def complete(
        self, *, system: str, user: str, max_tokens: int = 512
    ) -> LLMAnswer:
        del system, max_tokens
        for prefix, (text, confidence) in self.canned.items():
            if user.startswith(prefix):
                return LLMAnswer(text=text, confidence=confidence, cache_hit=True)
        return LLMAnswer(
            text="(no canned answer; returning a placeholder)",
            confidence=0.1,
            cache_hit=False,
        )


class AnthropicLLMClient:
    """Anthropic SDK adapter with system-prompt caching wired.

    Imports ``anthropic`` lazily so the rest of the example, including
    its tests, runs without the SDK installed. Install with the
    ``llm-examples`` extra: ``pip install pysakshi[llm-examples]``.
    Caches the system prompt with ``cache_control={"type": "ephemeral"}``
    so multi-cycle research sessions reuse the cached prefix and pay
    cache-read rates instead of full input rates.
    """

    def __init__(
        self,
        *,
        model: str = "claude-haiku-4-5-20251001",
        client: Any = None,
    ) -> None:
        if client is None:
            try:
                from anthropic import AsyncAnthropic  # type: ignore[import-not-found]
            except ImportError as exc:  # pragma: no cover - tested via mock client
                raise ImportError(
                    "anthropic SDK not installed. "
                    "Install with: pip install pysakshi[llm-examples]"
                ) from exc
            client = AsyncAnthropic()
        self._client: Any = client
        self._model = model

    async def complete(
        self, *, system: str, user: str, max_tokens: int = 512
    ) -> LLMAnswer:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=[
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user}],
        )
        text_blocks = [
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ]
        text = "\n".join(text_blocks).strip()
        usage = getattr(response, "usage", None)
        cache_read = bool(usage and getattr(usage, "cache_read_input_tokens", 0))
        return LLMAnswer(
            text=text,
            confidence=_extract_confidence(text),
            cache_hit=cache_read,
        )


def _extract_confidence(text: str) -> float:
    """Parse a ``Confidence: 0.X`` line out of a free-form LLM response.

    Falls back to 0.5 (neutral) when no marker is present, so the agent
    has *some* signal even with a malformed reply.
    """
    for line in text.splitlines():
        stripped = line.strip().lower()
        if stripped.startswith("confidence:"):
            tail = stripped.split(":", 1)[1].strip()
            try:
                value = float(tail.split()[0])
            except (ValueError, IndexError):
                continue
            return max(0.0, min(1.0, value))
    return 0.5
