from __future__ import annotations

import asyncio
import logging
import re

from fastapi import BackgroundTasks, UploadFile

from server.config import Settings, get_settings
from server.models.voice_node import AssistantAudioData, AssistantAudioResponse
from server.services.stt_service import STTService, get_stt_service
from server.services.tts_service import TTSService, get_tts_service
from server.services.voice_conversation_service import (
    VoiceConversationService,
    get_voice_conversation_service,
)
from server.services.voice_node_manager import VoiceNodeManager, get_voice_node_manager
from server.services.voice_node_text_normalizer import normalize_voice_node_transcript
from server.utils.observability import log_timing, start_timer

logger = logging.getLogger(__name__)

VOICE_NODE_WAKE_SOURCE = "voice_node_wake"
VOICE_NODE_WAKE_PHRASES: tuple[str, ...] = (
    "สวัสดีน้องฟ้า",
    "หวัดดีน้องฟ้า",
    "น้องฟ้า",
    "น้องฟ้าจ๋า",
)
VOICE_NODE_SLEEP_PHRASES: tuple[str, ...] = (
    "ขอบคุณ",
    "พอแล้ว",
    "หยุดฟัง",
    "เลิกคุย",
    "น้องฟ้าพักก่อน",
    "น้องฟ้าปิด",
    "ปิดน้องฟ้า",
)
VOICE_NODE_WAKE_ACK_REPLY = "ฟังอยู่ครับ พูดต่อได้เลย"
VOICE_NODE_SLEEP_REPLY = "ได้เลย น้องฟ้าจะรอฟังคำปลุกอยู่นะ"


class AssistantAudioService:
    """Voice Node audio upload pipeline: STT -> existing chat logic -> TTS URL."""

    def __init__(
        self,
        settings: Settings,
        stt_service: STTService,
        voice_conversation_service: VoiceConversationService,
        voice_node_manager: VoiceNodeManager,
        tts_service: TTSService,
    ) -> None:
        self._settings = settings
        self._stt_service = stt_service
        self._voice_conversation_service = voice_conversation_service
        self._voice_node_manager = voice_node_manager
        self._tts_service = tts_service

    async def handle_audio_upload(
        self,
        audio: UploadFile,
        device_id: str,
        pir_state: int,
        source: str,
        background_tasks: BackgroundTasks,
    ) -> AssistantAudioResponse:
        audio_bytes = await audio.read()
        return await self.handle_audio_bytes(
            audio_bytes=audio_bytes,
            filename=audio.filename,
            content_type=audio.content_type,
            device_id=device_id,
            pir_state=pir_state,
            source=source,
            background_tasks=background_tasks,
        )

    async def handle_audio_bytes(
        self,
        audio_bytes: bytes,
        filename: str | None,
        content_type: str | None,
        device_id: str,
        pir_state: int,
        source: str,
        background_tasks: BackgroundTasks,
    ) -> AssistantAudioResponse:
        timer = start_timer()
        status_text = "ok"

        try:
            audio_data, status_text = await asyncio.to_thread(
                self._process_audio_bytes,
                audio_bytes,
                filename,
                content_type,
                device_id,
                pir_state,
                source,
                background_tasks,
            )
            return AssistantAudioResponse(data=audio_data)
        except Exception:
            status_text = "error"
            raise
        finally:
            log_timing(
                logger,
                self._settings,
                "assistant.audio",
                timer.elapsed_ms,
                device_id=device_id,
                status=status_text,
            )

    def handle_no_speech_audio_bytes(
        self,
        audio_bytes: bytes,
        device_id: str,
        content_type: str | None,
        background_tasks: BackgroundTasks,
    ) -> AssistantAudioResponse:
        voice_data = self._voice_conversation_service.build_stt_unavailable_response(
            background_tasks=background_tasks,
            audio_mode="none",
        ).model_copy(
            update={
                "reply": "ยังไม่ได้ยินเสียงพูดชัด ๆ ลองพูดหลังเสียงติ๊ดให้ใกล้ไมค์อีกครั้งนะ",
                "keep_mic_open": False,
            }
        )
        reply_audio_url = self._synthesize_voice_node_reply(voice_data.reply)
        audio_data = AssistantAudioData(
            heard_text="",
            reply=voice_data.reply,
            intent=voice_data.intent,
            source=voice_data.source,
            action=voice_data.action,
            keep_mic_open=voice_data.keep_mic_open,
            reply_audio_url=self._resolve_reply_audio_url(reply_audio_url),
            reply_audio_format=self._settings.voice_node_reply_audio_format,
        )
        self._voice_node_manager.record_audio_result(
            device_id=device_id,
            stt_ok=False,
            stt_error="no speech detected",
            stt_raw_text="",
            data=audio_data,
            uploaded_audio_bytes=audio_bytes,
            uploaded_audio_content_type=content_type,
        )
        return AssistantAudioResponse(data=audio_data)

    def _process_audio_bytes(
        self,
        audio_bytes: bytes,
        filename: str | None,
        content_type: str | None,
        device_id: str,
        pir_state: int,
        source: str,
        background_tasks: BackgroundTasks,
    ) -> tuple[AssistantAudioData, str]:
        status_text = "ok"
        stt_result = self._stt_service.transcribe_bytes(
            filename=filename,
            content_type=content_type,
            audio_bytes=audio_bytes,
        )
        is_wake_upload = source.strip().lower() == VOICE_NODE_WAKE_SOURCE
        if not stt_result.ok:
            status_text = "stt_fallback"
            if is_wake_upload:
                audio_data = self._build_silent_wake_response(device_id=device_id)
                self._voice_node_manager.record_audio_result(
                    device_id=device_id,
                    stt_ok=False,
                    stt_error=stt_result.error,
                    stt_raw_text=stt_result.raw_text,
                    data=audio_data,
                    uploaded_audio_bytes=audio_bytes,
                    uploaded_audio_content_type=content_type,
                )
                return audio_data, status_text

            voice_data = self._voice_conversation_service.build_stt_unavailable_response(
                background_tasks=background_tasks,
                audio_mode="none",
            )
            if self._is_unclear_voice_result(stt_result.error):
                voice_data = voice_data.model_copy(
                    update={
                        "reply": "ยังไม่ได้ยินเสียงพูดชัด ๆ ลองพูดหลังเสียงติ๊ดให้ใกล้ไมค์อีกครั้งนะ",
                        "keep_mic_open": False,
                    }
                )
        else:
            normalized_text = normalize_voice_node_transcript(stt_result.text)
            if is_wake_upload:
                audio_data = self._handle_wake_upload(
                    heard_text=normalized_text,
                    device_id=device_id,
                    background_tasks=background_tasks,
                )
                self._voice_node_manager.record_audio_result(
                    device_id=device_id,
                    stt_ok=stt_result.ok,
                    stt_error=stt_result.error,
                    stt_raw_text=stt_result.raw_text,
                    data=audio_data,
                    uploaded_audio_bytes=audio_bytes,
                    uploaded_audio_content_type=content_type,
                )
                return audio_data, status_text

            voice_data = self._voice_conversation_service.handle_turn(
                heard_text=normalized_text,
                pir_state=pir_state,
                background_tasks=background_tasks,
                audio_mode="none",
            )

        reply_audio_url = self._synthesize_voice_node_reply(voice_data.reply)
        audio_data = AssistantAudioData(
            heard_text=voice_data.heard_text,
            reply=voice_data.reply,
            intent=voice_data.intent,
            source=voice_data.source,
            action=voice_data.action,
            keep_mic_open=voice_data.keep_mic_open,
            reply_audio_url=self._resolve_reply_audio_url(reply_audio_url),
            reply_audio_format=self._settings.voice_node_reply_audio_format,
        )
        self._voice_node_manager.record_audio_result(
            device_id=device_id,
            stt_ok=stt_result.ok,
            stt_error=stt_result.error,
            stt_raw_text=stt_result.raw_text,
            data=audio_data,
            uploaded_audio_bytes=audio_bytes,
            uploaded_audio_content_type=content_type,
        )
        return audio_data, status_text

    def _handle_wake_upload(
        self,
        heard_text: str,
        device_id: str,
        background_tasks: BackgroundTasks,
    ) -> AssistantAudioData:
        cleaned_text = heard_text.strip()
        active = self._voice_node_manager.is_wake_conversation_active(device_id)
        wake_remainder = self._extract_wake_remainder(cleaned_text)

        if not active:
            if wake_remainder is None:
                return self._build_silent_wake_response(
                    device_id=device_id,
                    heard_text=cleaned_text,
                )

            self._voice_node_manager.set_wake_conversation_active(device_id, True)
            cleaned_text = wake_remainder.strip()
            if not cleaned_text:
                return self._build_wake_response(
                    heard_text=heard_text,
                    reply=VOICE_NODE_WAKE_ACK_REPLY,
                    keep_mic_open=True,
                )

        if self._contains_sleep_phrase(cleaned_text):
            self._voice_node_manager.set_wake_conversation_active(device_id, False)
            return self._build_wake_response(
                heard_text=cleaned_text,
                reply=VOICE_NODE_SLEEP_REPLY,
                keep_mic_open=True,
            )

        if not cleaned_text:
            return self._build_silent_wake_response(device_id=device_id)

        voice_data = self._voice_conversation_service.handle_turn(
            heard_text=cleaned_text,
            pir_state=1,
            background_tasks=background_tasks,
            audio_mode="none",
        )
        if not voice_data.keep_mic_open:
            self._voice_node_manager.set_wake_conversation_active(device_id, False)

        reply_audio_url = self._synthesize_voice_node_reply(voice_data.reply)
        return AssistantAudioData(
            heard_text=voice_data.heard_text,
            reply=voice_data.reply,
            intent=voice_data.intent,
            source=voice_data.source,
            action=voice_data.action,
            keep_mic_open=True,
            reply_audio_url=self._resolve_reply_audio_url(reply_audio_url),
            reply_audio_format=self._settings.voice_node_reply_audio_format,
        )

    def _build_silent_wake_response(
        self,
        device_id: str,
        heard_text: str = "",
    ) -> AssistantAudioData:
        return AssistantAudioData(
            heard_text=heard_text,
            reply="",
            intent="general_chat",
            source="voice_control",
            action="none",
            keep_mic_open=True,
            reply_audio_url=None,
            reply_audio_format=self._settings.voice_node_reply_audio_format,
        )

    def _build_wake_response(
        self,
        heard_text: str,
        reply: str,
        keep_mic_open: bool,
    ) -> AssistantAudioData:
        reply_audio_url = self._synthesize_voice_node_reply(reply)
        return AssistantAudioData(
            heard_text=heard_text,
            reply=reply,
            intent="general_chat",
            source="voice_control",
            action="none",
            keep_mic_open=keep_mic_open,
            reply_audio_url=self._resolve_reply_audio_url(reply_audio_url),
            reply_audio_format=self._settings.voice_node_reply_audio_format,
        )

    @staticmethod
    def _is_unclear_voice_result(error: str | None) -> bool:
        if error is None:
            return False
        normalized_error = error.strip().lower()
        return normalized_error in {
            "no speech detected",
            "audio file is empty",
        }

    @classmethod
    def _extract_wake_remainder(cls, text: str) -> str | None:
        normalized_text = cls._normalize_for_wake(text)
        if not normalized_text:
            return None

        for phrase in VOICE_NODE_WAKE_PHRASES:
            normalized_phrase = cls._normalize_for_wake(phrase)
            index = normalized_text.find(normalized_phrase)
            if index < 0:
                continue
            remainder_start = index + len(normalized_phrase)
            compact_remainder = normalized_text[remainder_start:]
            return cls._strip_wake_phrase_from_original(text, phrase, compact_remainder)
        return None

    @classmethod
    def _contains_sleep_phrase(cls, text: str) -> bool:
        normalized_text = cls._normalize_for_wake(text)
        return any(
            cls._normalize_for_wake(phrase) in normalized_text
            for phrase in VOICE_NODE_SLEEP_PHRASES
        )

    @staticmethod
    def _normalize_for_wake(text: str) -> str:
        return "".join(text.casefold().split())

    @staticmethod
    def _strip_wake_phrase_from_original(
        text: str,
        phrase: str,
        compact_remainder: str,
    ) -> str:
        pattern = r"\s*".join(re.escape(character) for character in phrase)
        stripped = re.sub(pattern, "", text, count=1, flags=re.IGNORECASE).strip(" ,:;.!?ๆ")
        if stripped:
            return stripped
        return compact_remainder

    def _synthesize_voice_node_reply(self, reply: str) -> str | None:
        if not self._settings.tts_enabled:
            return None

        spoken_reply = self._build_spoken_reply(reply)
        if not spoken_reply:
            return None

        tts_result = self._tts_service.synthesize(spoken_reply)
        if not tts_result.ok:
            logger.warning("Voice node TTS generation failed: %s", tts_result.error)
            return None
        return tts_result.audio_url

    def _build_spoken_reply(self, reply: str) -> str:
        cleaned_reply = " ".join(reply.split())
        max_chars = max(60, self._settings.voice_node_spoken_reply_max_chars)
        news_reply = self._build_news_spoken_reply(cleaned_reply, max_chars)
        if news_reply is not None:
            return news_reply

        cleaned_reply = self._normalize_spoken_text(cleaned_reply)
        if len(cleaned_reply) <= max_chars:
            return cleaned_reply

        notice = " ถ้าอยากฟังต่อ บอกได้เลย"
        target_chars = max(40, max_chars - len(notice))
        selected_reply = self._first_sentence_chunk(cleaned_reply, target_chars)
        return f"{selected_reply}{notice}".strip()

    def _build_news_spoken_reply(self, reply: str, max_chars: int) -> str | None:
        if "ข่าว" not in reply or "1." not in reply:
            return None

        count_match = re.search(r"มี\s*(\d+)\s*เรื่อง", reply)
        count_text = count_match.group(1) if count_match else "หลาย"
        headline_match = re.search(r"1\.\s*(.*?)(?:\s*\|\s*2\.|$)", reply)
        if headline_match is None:
            return None

        first_headline = self._normalize_spoken_text(headline_match.group(1))
        first_headline = re.split(r"ถ้าอยากฟังต่อ|บอกเลขข้อ|ส่งข่าวเข้า", first_headline)[0].strip()
        first_headline = self._first_sentence_chunk(first_headline, 48)
        spoken = (
            f"ข่าวล่าสุดมี {count_text} เรื่อง "
            f"ข้อ 1 {first_headline} "
            "ถ้าอยากฟังต่อ บอกเลขข้อ หรือบอก ส่งข่าวเข้าไลน์"
        )
        if len(spoken) <= max_chars:
            return spoken
        compact_spoken = (
            f"ข่าวล่าสุดมี {count_text} เรื่อง "
            f"ข้อ 1 {self._first_sentence_chunk(first_headline, 32)} "
            "บอกเลขข้อ หรือบอก ส่งข่าวเข้าไลน์"
        )
        return compact_spoken

    @staticmethod
    def _normalize_spoken_text(text: str) -> str:
        return (
            text.replace("|", " ")
            .replace("LINE", "ไลน์")
            .replace("line", "ไลน์")
            .replace("URL", "ลิงก์")
            .replace("url", "ลิงก์")
            .strip()
        )

    @staticmethod
    def _first_sentence_chunk(text: str, max_chars: int) -> str:
        chunks = re.split(r"(?<=[.!?。！？])\s+|\s*\|\s*", text)
        selected_chunks: list[str] = []
        current_length = 0
        for chunk in chunks:
            cleaned_chunk = chunk.strip()
            if not cleaned_chunk:
                continue
            next_length = current_length + len(cleaned_chunk) + (1 if selected_chunks else 0)
            if selected_chunks and next_length > max_chars:
                break
            selected_chunks.append(cleaned_chunk)
            current_length = next_length
            if current_length >= max_chars:
                break

        selected = " ".join(selected_chunks).strip()
        if not selected:
            selected = text[:max_chars].strip()
        if len(selected) > max_chars:
            selected = selected[:max_chars].rstrip(" ,|-")
        return selected

    def _resolve_reply_audio_url(self, audio_url: str | None) -> str | None:
        voice_node_url = self._voice_node_manager.to_voice_node_audio_url(audio_url)
        if (
            voice_node_url is not None
            and self._settings.voice_node_reply_audio_format.strip().lower() == "wav"
        ):
            voice_node_url = voice_node_url.replace(
                "/voice-node/audio/current",
                "/voice-node/audio/current.wav",
                1,
            )
        return voice_node_url


_assistant_audio_service = AssistantAudioService(
    settings=get_settings(),
    stt_service=get_stt_service(),
    voice_conversation_service=get_voice_conversation_service(),
    voice_node_manager=get_voice_node_manager(),
    tts_service=get_tts_service(),
)


def get_assistant_audio_service() -> AssistantAudioService:
    return _assistant_audio_service
