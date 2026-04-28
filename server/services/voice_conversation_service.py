from __future__ import annotations

import json
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path

from fastapi import BackgroundTasks

from server.config import Settings, get_settings
from server.models.chat import IntentName, ResponseSource
from server.models.voice import MicAction, VoiceChatData
from server.services.chat_service import ChatService, get_chat_service
from server.services.intent_router import IntentRouter, get_intent_router
from server.services.llm_manager import DEFAULT_FALLBACK_REPLY, LLMManager, get_llm_manager
from server.services.smalltalk_service import SmallTalkService, get_smalltalk_service
from server.services.tts_service import TTSService, get_tts_service
from server.utils.reply_cleaner import clean_reply_text

EXIT_WORDS: tuple[str, ...] = (
    "ขอบคุณ",
    "พอแล้ว",
    "แค่นี้แหละ",
    "เลิกคุย",
    "หยุดฟัง",
    "ไปได้แล้ว",
)
VOICE_EXIT_REPLY = "ได้เลย ถ้าต้องการคุยต่อเมื่อไรก็บอกได้เสมอนะ"
VOICE_UNAVAILABLE_REPLY = "ตอนนี้ระบบฟังเสียงยังไม่พร้อม ลองพูดใหม่อีกครั้งหรือพิมพ์ข้อความแทนก่อนได้ไหม"
VOICE_CONTROL_PROMPT_FALLBACK = (
    "ตอบเป็น JSON object เดียวเท่านั้น โดยมีคีย์ reply, action, keep_mic_open "
    "ตอบภาษาไทยสั้น สุภาพ keep_mic_open เป็น true เฉพาะเมื่อควรถามต่อหรือชวนคุยต่อ"
)
FOLLOW_UP_CUES: tuple[str, ...] = (
    "เอาข้อไหน",
    "อยากฟังต่อ",
    "อยากให้เล่าต่อ",
    "อยากให้ช่วยอะไรต่อ",
    "อยากถามต่อไหม",
    "ต้องการให้ช่วยต่อไหม",
)
VALID_ACTIONS: set[str] = {"none", "light_on", "light_off", "relay_on", "relay_off"}


@dataclass(frozen=True)
class VoiceControlDecision:
    reply: str
    action: MicAction
    keep_mic_open: bool
    source: ResponseSource


class VoiceConversationService:
    def __init__(
        self,
        settings: Settings,
        chat_service: ChatService,
        intent_router: IntentRouter,
        llm_manager: LLMManager,
        smalltalk_service: SmallTalkService,
        tts_service: TTSService,
    ) -> None:
        self._settings = settings
        self._chat_service = chat_service
        self._intent_router = intent_router
        self._llm_manager = llm_manager
        self._smalltalk_service = smalltalk_service
        self._tts_service = tts_service

    def handle_turn(
        self,
        heard_text: str,
        pir_state: int,
        background_tasks: BackgroundTasks,
    ) -> VoiceChatData:
        cleaned_text = heard_text.strip()
        if not cleaned_text:
            return self._build_response(
                heard_text="",
                reply=VOICE_UNAVAILABLE_REPLY,
                intent="general_chat",
                source="fallback",
                action="none",
                keep_mic_open=False,
                background_tasks=background_tasks,
            )

        if self._contains_exit_word(cleaned_text):
            return self._build_response(
                heard_text=cleaned_text,
                reply=VOICE_EXIT_REPLY,
                intent="general_chat",
                source="voice_control",
                action="none",
                keep_mic_open=False,
                background_tasks=background_tasks,
            )

        intent = self._intent_router.classify(cleaned_text).intent
        if intent == "general_chat":
            smalltalk_reply = self._smalltalk_service.get_reply(cleaned_text)
            if smalltalk_reply is not None:
                keep_mic_open = self._apply_keep_mic_open_override(
                    ai_keep_mic_open=smalltalk_reply.keep_mic_open,
                    pir_state=pir_state,
                    is_exit_turn=False,
                )
                return self._build_response(
                    heard_text=cleaned_text,
                    reply=smalltalk_reply.reply,
                    intent="general_chat",
                    source="rule_based",
                    action="none",
                    keep_mic_open=keep_mic_open,
                    background_tasks=background_tasks,
                )

            decision = self._handle_general_chat(cleaned_text)
            keep_mic_open = self._apply_keep_mic_open_override(
                ai_keep_mic_open=decision.keep_mic_open,
                pir_state=pir_state,
                is_exit_turn=False,
            )
            return self._build_response(
                heard_text=cleaned_text,
                reply=decision.reply,
                intent="general_chat",
                source=decision.source,
                action=decision.action,
                keep_mic_open=keep_mic_open,
                background_tasks=background_tasks,
            )

        chat_response = self._chat_service.handle_message(
            cleaned_text,
            background_tasks=background_tasks,
            suppress_audio=True,
        )
        action = self._infer_action(intent=chat_response.intent, message=cleaned_text)
        ai_keep_mic_open = self._infer_non_llm_keep_mic_open(
            intent=chat_response.intent,
            reply=chat_response.reply,
        )
        keep_mic_open = self._apply_keep_mic_open_override(
            ai_keep_mic_open=ai_keep_mic_open,
            pir_state=pir_state,
            is_exit_turn=False,
        )
        return self._build_response(
            heard_text=cleaned_text,
            reply=chat_response.reply,
            intent=chat_response.intent,
            source=chat_response.source,
            action=action,
            keep_mic_open=keep_mic_open,
            background_tasks=background_tasks,
        )

    def build_stt_unavailable_response(
        self,
        background_tasks: BackgroundTasks,
    ) -> VoiceChatData:
        return self._build_response(
            heard_text="",
            reply=VOICE_UNAVAILABLE_REPLY,
            intent="general_chat",
            source="fallback",
            action="none",
            keep_mic_open=False,
            background_tasks=background_tasks,
        )

    def _handle_general_chat(self, message: str) -> VoiceControlDecision:
        raw_response = self._llm_manager.generate_custom_reply(
            message=self._build_general_chat_input(message),
            system_prompt=self._load_voice_control_prompt(),
            max_tokens=min(self._settings.llm_max_tokens, 96),
            temperature=min(self._settings.llm_temperature, 0.2),
            log_mode="voice_control",
        )
        parsed = self._parse_voice_control_json(raw_response.reply)
        if parsed is not None:
            return parsed

        fallback_reply = clean_reply_text(raw_response.reply, fallback=DEFAULT_FALLBACK_REPLY)
        return VoiceControlDecision(
            reply=fallback_reply,
            action="none",
            keep_mic_open=False,
            source=raw_response.source,
        )

    @staticmethod
    def _build_general_chat_input(message: str) -> str:
        return f"ข้อความผู้ใช้ล่าสุด:\n{message}"

    def _build_response(
        self,
        heard_text: str,
        reply: str,
        intent: IntentName,
        source: ResponseSource,
        action: MicAction,
        keep_mic_open: bool,
        background_tasks: BackgroundTasks,
    ) -> VoiceChatData:
        audio_url = None
        if self._settings.tts_enabled:
            token, audio_url = self._tts_service.create_pending_audio_url()
            background_tasks.add_task(self._tts_service.synthesize, reply, token)
        return VoiceChatData(
            heard_text=heard_text,
            reply=reply,
            intent=intent,
            source=source,
            action=action,
            keep_mic_open=keep_mic_open,
            audio_url=audio_url,
        )

    @staticmethod
    def _contains_exit_word(message: str) -> bool:
        normalized = VoiceConversationService._normalize(message)
        return any(VoiceConversationService._normalize(word) in normalized for word in EXIT_WORDS)

    def _infer_non_llm_keep_mic_open(self, intent: IntentName, reply: str) -> bool:
        normalized_reply = self._normalize(reply)
        if any(self._normalize(cue) in normalized_reply for cue in FOLLOW_UP_CUES):
            return True
        return intent in {"news_query", "news_detail_query"} and "?" in reply

    def _apply_keep_mic_open_override(
        self,
        ai_keep_mic_open: bool,
        pir_state: int,
        is_exit_turn: bool,
    ) -> bool:
        if is_exit_turn:
            return False
        if not ai_keep_mic_open and pir_state == 1:
            return True
        if pir_state == 0:
            return ai_keep_mic_open
        return ai_keep_mic_open if ai_keep_mic_open else False

    @staticmethod
    def _infer_action(intent: IntentName, message: str) -> MicAction:
        if intent != "device_control":
            return "none"

        normalized = VoiceConversationService._normalize(message)
        is_on = "เปิด" in normalized
        if "ไฟ" in normalized:
            return "light_on" if is_on else "light_off"
        return "relay_on" if is_on else "relay_off"

    def _parse_voice_control_json(self, raw_text: str) -> VoiceControlDecision | None:
        payload = self._extract_first_json_object(raw_text)
        if payload is None:
            return None

        reply = clean_reply_text(str(payload.get("reply", "")), fallback="")
        action = str(payload.get("action", "none")).strip().lower()
        keep_mic_open = payload.get("keep_mic_open")

        if not reply:
            return None
        if action not in VALID_ACTIONS:
            action = "none"
        if not isinstance(keep_mic_open, bool):
            return None

        return VoiceControlDecision(
            reply=reply,
            action=action,  # type: ignore[arg-type]
            keep_mic_open=keep_mic_open,
            source="ollama",
        )

    @staticmethod
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

    def _load_voice_control_prompt(self) -> str:
        prompt_path = Path(__file__).resolve().parents[2] / "prompts" / "voice_control_prompt.txt"
        try:
            prompt_text = prompt_path.read_text(encoding="utf-8").strip()
        except OSError:
            return VOICE_CONTROL_PROMPT_FALLBACK
        return prompt_text or VOICE_CONTROL_PROMPT_FALLBACK

    @staticmethod
    def _normalize(text: str) -> str:
        return "".join(text.casefold().split())


_voice_conversation_service = VoiceConversationService(
    settings=get_settings(),
    chat_service=get_chat_service(),
    intent_router=get_intent_router(),
    llm_manager=get_llm_manager(),
    smalltalk_service=get_smalltalk_service(),
    tts_service=get_tts_service(),
)


def get_voice_conversation_service() -> VoiceConversationService:
    return _voice_conversation_service
