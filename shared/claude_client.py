"""Thin Anthropic SDK wrapper that applies prompt caching sensibly.

Caching strategy:
- The static `system` prompt is marked cache-control so it's billed once per TTL.
- Optional `cached_user_blocks` (e.g. reference context, tool definitions list as
  text, editorial guide) also get a cache breakpoint.
- The actual user turn + tool results go in the tail without cache_control.
"""

from __future__ import annotations

from typing import Any, Iterable

from anthropic import Anthropic

from .config import env

_client: Anthropic | None = None


def client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=env("ANTHROPIC_API_KEY", required=True))
    return _client


def _system_blocks(system_text: str, cached_reference: str | None) -> list[dict]:
    blocks: list[dict] = [
        {
            "type": "text",
            "text": system_text,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    if cached_reference:
        blocks.append(
            {
                "type": "text",
                "text": cached_reference,
                "cache_control": {"type": "ephemeral"},
            }
        )
    return blocks


def call(
    *,
    system: str,
    cached_reference: str | None = None,
    messages: list[dict],
    model: str,
    max_tokens: int = 4096,
    tools: Iterable[dict] | None = None,
    temperature: float = 0.3,
) -> Any:
    """One-shot call. Returns the raw Anthropic Message object."""
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": _system_blocks(system, cached_reference),
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        kwargs["tools"] = list(tools)
    return client().messages.create(**kwargs)


def extract_text(message: Any) -> str:
    """Concatenate all top-level text blocks from a Message."""
    parts: list[str] = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts)
