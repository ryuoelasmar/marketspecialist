"""Turn a raw market+news bundle into a structured digest via Claude."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, is_dataclass
from typing import Any

from shared import claude_client
from shared.config import env
from shared.prompts import load_prompt


def _json_default(obj: Any):
    if is_dataclass(obj):
        return asdict(obj)
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


def _extract_json(text: str) -> dict:
    """Robustly parse JSON, stripping accidental markdown fences."""
    text = text.strip()
    # Strip ```json ... ``` fences if present.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    return json.loads(text)


def synthesize(bundle: dict, model: str | None = None) -> dict:
    """bundle: {'date': ..., 'markets': [...], 'news': [...], 'macro': [...]}

    Returns the structured digest dict matching the schema in digest_system.md.
    """
    system = load_prompt("digest_system")
    model = model or env("DIGEST_MODEL", "claude-sonnet-4-6")

    user_payload = json.dumps(bundle, default=_json_default, ensure_ascii=False, indent=2)
    messages = [
        {
            "role": "user",
            "content": (
                "Here is today's raw data bundle (markets, news, macro). "
                "Follow the schema and rules in your system prompt exactly.\n\n"
                f"```json\n{user_payload}\n```"
            ),
        }
    ]

    msg = claude_client.call(
        system=system,
        messages=messages,
        model=model,
        max_tokens=4096,
        temperature=0.2,
    )
    text = claude_client.extract_text(msg)
    try:
        return _extract_json(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Digest output was not valid JSON: {e}\n\n---\n{text[:2000]}")
