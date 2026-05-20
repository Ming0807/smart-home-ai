from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import re
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
        self._user_names: dict[str, str] = {}
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

    def get_fast_reply(self, session_id: str, message: str) -> str | None:
        """Handle tiny personal-memory turns without waking the LLM."""
        cleaned_message = " ".join(message.split()).strip()
        if not cleaned_message:
            return None

        name = self._extract_user_name(cleaned_message)
        if name is not None:
            with self._lock:
                self._user_names[session_id] = name
            return f"จำได้แล้ว คุณ{name}"

        if self._is_name_question(cleaned_message):
            with self._lock:
                stored_name = self._user_names.get(session_id)
            if stored_name:
                return f"คุณชื่อ{stored_name}"
            return "ยังไม่รู้ชื่อคุณเลย บอกชื่อให้ฉันจำได้เลยนะ"

        return None

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

    @staticmethod
    def _extract_user_name(message: str) -> str | None:
        normalized = "".join(message.casefold().split())
        if "ชื่ออะไร" in normalized or "ชื่อใคร" in normalized:
            return None
        match = re.search(
            r"(?:ฉัน|ผม|หนู|เรา|ข้า)?\s*ชื่อ\s*([ก-๙A-Za-z0-9_.-]{1,40})",
            message,
        )
        if match is None:
            return None
        name = match.group(1).strip()
        name = re.sub(r"(ครับ|ค่ะ|คะ|นะ|จ้า|จ๊ะ)$", "", name).strip()
        return name or None

    @staticmethod
    def _is_name_question(message: str) -> bool:
        normalized = "".join(message.casefold().split())
        return any(
            keyword in normalized
            for keyword in (
                "ชื่ออะไร",
                "ฉันชื่ออะไร",
                "ผมชื่ออะไร",
                "จำชื่อฉันได้ไหม",
                "จำชื่อผมได้ไหม",
                "เมื่อกี้ฉันบอกว่าชื่ออะไร",
                "เมื่อกี้ผมบอกว่าชื่ออะไร",
            )
        )


_conversation_memory_service = ConversationMemoryService(settings=get_settings())


def get_conversation_memory_service() -> ConversationMemoryService:
    return _conversation_memory_service
