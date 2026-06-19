import io
import unittest
import wave

from fastapi import BackgroundTasks

from server.config import Settings
from server.services.assistant_audio_service import AssistantAudioService
from server.services.stt_service import STTResult
from server.services.tts_service import TTSResult
from server.services.voice_node_manager import VoiceNodeManager


class FailOnHandleTurn:
    def handle_turn(self, *args, **kwargs):
        raise AssertionError("wake upload without wake word must stay silent")


class NoopTTSService:
    def synthesize(self, text: str) -> TTSResult:
        return TTSResult(
            ok=True,
            text=text,
            audio_url="/voice/audio/current?token=test-token",
            token="test-token",
        )


class CapturingSTTService:
    def __init__(self, error: str = "no speech detected") -> None:
        self.error = error
        self.retry_without_vad_values: list[bool] = []

    def transcribe_bytes(
        self,
        filename: str | None,
        content_type: str | None,
        audio_bytes: bytes,
        retry_without_vad: bool = True,
    ) -> STTResult:
        self.retry_without_vad_values.append(retry_without_vad)
        return STTResult(
            ok=False,
            text="",
            provider="fake",
            error=self.error,
            raw_text="" if self.error == "no speech detected" else None,
        )


def make_silent_wav() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00" * 1600)
    return buffer.getvalue()


class VoiceNodeSpuriousFilterTest(unittest.TestCase):
    def test_short_time_context_is_meaningful(self) -> None:
        meaningful_texts = [
            "\u0e27\u0e31\u0e19\u0e19\u0e35\u0e49",
            "\u0e15\u0e2d\u0e19\u0e19\u0e35\u0e49",
        ]

        for text in meaningful_texts:
            with self.subTest(text=text):
                self.assertFalse(
                    AssistantAudioService._is_likely_spurious_voice_node_text(
                        "voice_node",
                        text,
                    )
                )

    def test_short_fillers_stay_spurious(self) -> None:
        filler_texts = [
            "\u0e2d\u0e37\u0e21",
            "\u0e04\u0e23\u0e31\u0e1a",
        ]

        for text in filler_texts:
            with self.subTest(text=text):
                self.assertTrue(
                    AssistantAudioService._is_likely_spurious_voice_node_text(
                        "voice_node",
                        text,
                    )
                )

    def test_wake_upload_direct_command_without_wake_word_stays_silent(self) -> None:
        manager = VoiceNodeManager(Settings())
        service = AssistantAudioService(
            settings=Settings(),
            stt_service=None,  # type: ignore[arg-type]
            voice_conversation_service=FailOnHandleTurn(),  # type: ignore[arg-type]
            voice_node_manager=manager,
            tts_service=NoopTTSService(),  # type: ignore[arg-type]
        )

        response = service._handle_wake_upload(
            heard_text="\u0e27\u0e31\u0e19\u0e19\u0e35\u0e49\u0e1d\u0e19\u0e08\u0e30\u0e15\u0e01\u0e44\u0e2b\u0e21",
            device_id="voice-node-01",
            background_tasks=BackgroundTasks(),
        )

        status = manager.get_status(device_id="voice-node-01")
        self.assertEqual(response.reply, "")
        self.assertIsNone(response.reply_audio_url)
        self.assertTrue(response.keep_mic_open)
        self.assertFalse(status.wake_conversation_active)
        self.assertEqual(status.pending_command_count, 0)

    def test_wake_phrase_only_queues_conversation_handoff(self) -> None:
        manager = VoiceNodeManager(Settings())
        service = AssistantAudioService(
            settings=Settings(),
            stt_service=None,  # type: ignore[arg-type]
            voice_conversation_service=FailOnHandleTurn(),  # type: ignore[arg-type]
            voice_node_manager=manager,
            tts_service=NoopTTSService(),  # type: ignore[arg-type]
        )

        response = service._handle_wake_upload(
            heard_text="\u0e2a\u0e27\u0e31\u0e2a\u0e14\u0e35\u0e19\u0e49\u0e2d\u0e07\u0e1f\u0e49\u0e32",
            device_id="voice-node-01",
            background_tasks=BackgroundTasks(),
        )

        command = manager.pop_next_command(device_id="voice-node-01").command
        self.assertNotEqual(response.reply, "")
        self.assertEqual(command.type if command else None, "conversation_start")

    def test_voice_node_conversation_retries_stt_without_vad(self) -> None:
        stt_service = CapturingSTTService()
        service = AssistantAudioService(
            settings=Settings(),
            stt_service=stt_service,  # type: ignore[arg-type]
            voice_conversation_service=FailOnHandleTurn(),  # type: ignore[arg-type]
            voice_node_manager=VoiceNodeManager(Settings()),
            tts_service=NoopTTSService(),  # type: ignore[arg-type]
        )

        response, _ = service._process_audio_bytes(
            audio_bytes=make_silent_wav(),
            filename="command.wav",
            content_type="audio/wav",
            device_id="voice-node-01",
            pir_state=1,
            source="voice_node",
            background_tasks=BackgroundTasks(),
        )

        self.assertEqual(stt_service.retry_without_vad_values, [True])
        self.assertNotEqual(response.reply, "")
        self.assertIsNotNone(response.reply_audio_url)

    def test_voice_node_memory_pressure_has_audible_feedback(self) -> None:
        stt_service = CapturingSTTService(error="stt memory pressure")
        service = AssistantAudioService(
            settings=Settings(),
            stt_service=stt_service,  # type: ignore[arg-type]
            voice_conversation_service=FailOnHandleTurn(),  # type: ignore[arg-type]
            voice_node_manager=VoiceNodeManager(Settings()),
            tts_service=NoopTTSService(),  # type: ignore[arg-type]
        )

        response, _ = service._process_audio_bytes(
            audio_bytes=make_silent_wav(),
            filename="command.wav",
            content_type="audio/wav",
            device_id="voice-node-01",
            pir_state=1,
            source="voice_node",
            background_tasks=BackgroundTasks(),
        )

        self.assertEqual(stt_service.retry_without_vad_values, [True])
        self.assertNotEqual(response.reply, "")
        self.assertIsNotNone(response.reply_audio_url)

    def test_wake_listen_retries_stt_but_stays_silent_on_failure(self) -> None:
        stt_service = CapturingSTTService()
        service = AssistantAudioService(
            settings=Settings(),
            stt_service=stt_service,  # type: ignore[arg-type]
            voice_conversation_service=FailOnHandleTurn(),  # type: ignore[arg-type]
            voice_node_manager=VoiceNodeManager(Settings()),
            tts_service=NoopTTSService(),  # type: ignore[arg-type]
        )

        response, _ = service._process_audio_bytes(
            audio_bytes=make_silent_wav(),
            filename="wake.wav",
            content_type="audio/wav",
            device_id="voice-node-01",
            pir_state=1,
            source="voice_node_wake",
            background_tasks=BackgroundTasks(),
        )

        self.assertEqual(stt_service.retry_without_vad_values, [True])
        self.assertEqual(response.reply, "")
        self.assertIsNone(response.reply_audio_url)


if __name__ == "__main__":
    unittest.main()
