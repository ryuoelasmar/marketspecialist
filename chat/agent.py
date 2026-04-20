"""Claude agent loop with tool use + prompt caching."""

from __future__ import annotations

from typing import Iterator

from anthropic.types import Message

from chat.tools import TOOLS, run_tool
from shared import claude_client
from shared.config import env
from shared.prompts import load_prompt


MAX_TURNS = 8


def _to_messages_for_api(history: list[dict]) -> list[dict]:
    """history is a list of {role, content} dicts; content may be a string or a
    list of blocks. For prompt caching, mark a cache breakpoint on the most
    recent user message so the preceding history stays cached."""
    if not history:
        return history
    out = [dict(m) for m in history]
    # Place cache_control on the last block of the last user-ish message.
    for m in reversed(out):
        if m["role"] == "user":
            content = m["content"]
            if isinstance(content, str):
                m["content"] = [
                    {
                        "type": "text",
                        "text": content,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            elif isinstance(content, list) and content:
                last = dict(content[-1])
                last["cache_control"] = {"type": "ephemeral"}
                m["content"] = content[:-1] + [last]
            break
    return out


def run_agent(history: list[dict], model: str | None = None) -> Iterator[dict]:
    """Stream events: {'type': 'assistant_text', 'text': ...}
                      {'type': 'tool_use', 'name': ..., 'input': ...}
                      {'type': 'tool_result', 'name': ..., 'output': ...}
                      {'type': 'final', 'text': ...}

    history is a mutable list of messages that this function appends to as the
    agent runs. Caller persists/renders it after the generator exits.
    """
    system = load_prompt("chat_system")
    model = model or env("CHAT_MODEL", "claude-sonnet-4-6")

    for _ in range(MAX_TURNS):
        messages = _to_messages_for_api(history)
        msg: Message = claude_client.call(
            system=system,
            messages=messages,
            model=model,
            tools=TOOLS,
            max_tokens=2048,
            temperature=0.3,
        )

        assistant_content: list[dict] = []
        tool_uses: list[dict] = []
        text_parts: list[str] = []

        for block in msg.content:
            if block.type == "text":
                text_parts.append(block.text)
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                tool_uses.append(
                    {"id": block.id, "name": block.name, "input": block.input}
                )
                assistant_content.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )

        if text_parts:
            yield {"type": "assistant_text", "text": "".join(text_parts)}

        history.append({"role": "assistant", "content": assistant_content})

        if msg.stop_reason != "tool_use" or not tool_uses:
            yield {"type": "final", "text": "".join(text_parts)}
            return

        tool_result_blocks = []
        for tu in tool_uses:
            yield {"type": "tool_use", "name": tu["name"], "input": tu["input"]}
            output = run_tool(tu["name"], tu["input"])
            yield {"type": "tool_result", "name": tu["name"], "output": output}
            tool_result_blocks.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tu["id"],
                    "content": output,
                }
            )

        history.append({"role": "user", "content": tool_result_blocks})

    yield {"type": "final", "text": "(reached max tool-use turns)"}
