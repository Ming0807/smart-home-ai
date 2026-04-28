from __future__ import annotations

import json
from json import JSONDecodeError


def clean_reply_text(raw_text: str, fallback: str = "") -> str:
    """Return user-facing reply text, even if an LLM leaks a JSON contract."""
    text = _strip_code_fence(str(raw_text or "").strip())
    if not text:
        return fallback

    payload = _extract_first_json_object(text)
    if isinstance(payload, dict):
        reply = payload.get("reply")
        if isinstance(reply, str) and reply.strip():
            return _strip_code_fence(reply.strip())

    loose_reply = _extract_loose_reply_field(text)
    if loose_reply:
        return _strip_code_fence(loose_reply)

    return text


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if len(lines) >= 2 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return stripped.strip("`").strip()


def _extract_first_json_object(raw_text: str) -> dict[str, object] | None:
    decoder = json.JSONDecoder()
    for index, character in enumerate(raw_text):
        if character != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(raw_text[index:])
        except JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _extract_loose_reply_field(text: str) -> str | None:
    marker = '"reply"'
    start = text.find(marker)
    if start == -1:
        marker = "reply"
        start = text.casefold().find(marker)
        if start == -1:
            return None

    colon = text.find(":", start + len(marker))
    if colon == -1:
        return None

    quote = text.find('"', colon + 1)
    if quote == -1:
        return None

    chars: list[str] = []
    escaped = False
    for char in text[quote + 1 :]:
        if escaped:
            chars.append(_unescape_json_char(char))
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            break
        chars.append(char)

    reply = "".join(chars).strip()
    return reply or None


def _unescape_json_char(char: str) -> str:
    if char == "n":
        return "\n"
    if char == "r":
        return "\r"
    if char == "t":
        return "\t"
    return char
