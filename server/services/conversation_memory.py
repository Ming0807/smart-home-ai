from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Lock

from server.config import Settings, get_settings


@dataclass(frozen=True)
class ConversationTurn:
    user: str
    assistant: str
    intent: str
    source: str


class ConversationMemoryService:
    """Small in-memory conversation memory for demo continuity.

    This is intentionally lightweight and process-local. It gives the LLM enough
    recent context for natural follow-ups without changing API contracts.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._turns: dict[str, deque[ConversationTurn]] = {}
        self._lock = Lock()

    def add_turn(
        self,
        session_id: str,
        user: str,
        assistant: str,
        intent: str,
        source: str,
    ) -> None:
        cleaned_user = " ".join(user.split()).strip()
        cleaned_assistant = " ".join(assistant.split()).strip()
        if not cleaned_user or not cleaned_assistant:
            return

        max_items = max(4, min(self._settings.max_chat_history_items, 50))
        with self._lock:
            turns = self._turns.setdefault(session_id, deque(maxlen=max_items))
            turns.append(
                ConversationTurn(
                    user=cleaned_user,
                    assistant=cleaned_assistant,
                    intent=intent,
                    source=source,
                )
            )

    def build_contextual_message(
        self,
        session_id: str,
        message: str,
        max_turns: int = 4,
        max_chars: int = 1400,
    ) -> str:
        cleaned_message = message.strip()
        with self._lock:
            turns = list(self._turns.get(session_id, ()))

        if not turns:
            return cleaned_message

        recent_turns = turns[-max_turns:]
        lines = [
            "บริบทบทสนทนาล่าสุด ใช้เพื่อเข้าใจคำถามต่อเนื่องเท่านั้น:",
        ]
        for turn in recent_turns:
            lines.append(f"ผู้ใช้: {turn.user}")
            lines.append(f"ผู้ช่วย: {turn.assistant}")
        lines.append("")
        lines.append(f"ข้อความผู้ใช้ล่าสุด: {cleaned_message}")
        contextual_message = "\n".join(lines)
        if len(contextual_message) <= max_chars:
            return contextual_message
        return contextual_message[-max_chars:]


_conversation_memory_service = ConversationMemoryService(settings=get_settings())


def get_conversation_memory_service() -> ConversationMemoryService:
    return _conversation_memory_service
