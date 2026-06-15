import unittest
from datetime import datetime, timedelta, timezone

from server.config import Settings
from server.models.voice_node import VoiceNodeHeartbeatRequest
from server.routes.voice_node import _queue_conversation_timeout_notice
from server.services.tts_service import TTSResult
from server.services.voice_node_manager import VoiceNodeManager


class FakeTTSService:
    def __init__(self) -> None:
        self.synthesized_text: str | None = None

    def synthesize(self, text: str) -> TTSResult:
        self.synthesized_text = text
        return TTSResult(
            ok=True,
            text=text,
            audio_url="/voice/audio/current?token=test-token",
            token="test-token",
        )


class VoiceNodeManagerTimeoutTest(unittest.TestCase):
    def test_stale_conversation_requests_timeout_notice_once(self) -> None:
        device_id = "voice-node-01"
        manager = VoiceNodeManager(Settings(voice_node_timeout_seconds=30.0))
        manager.queue_command("conversation_start", device_id=device_id)
        manager.pop_next_command(device_id=device_id)

        with manager._lock:
            manager._conversation_mode_enabled[device_id] = True
            manager._conversation_mode_started_at[device_id] = (
                datetime.now(timezone.utc) - timedelta(seconds=40)
            )
            manager._wake_mode_enabled[device_id] = True

        manager.record_heartbeat(
            VoiceNodeHeartbeatRequest(
                device_id=device_id,
                state="WAKE_LISTENING",
            )
        )

        status = manager.get_status(device_id=device_id)
        self.assertFalse(status.conversation_mode_enabled)
        self.assertFalse(status.wake_conversation_active)
        self.assertEqual(status.pending_command_count, 0)
        self.assertTrue(manager.pop_conversation_timeout_notice(device_id))
        self.assertFalse(manager.pop_conversation_timeout_notice(device_id))

    def test_timeout_notice_queues_stop_audio_then_wake_start(self) -> None:
        device_id = "voice-node-01"
        settings = Settings(voice_node_reply_audio_format="wav")
        manager = VoiceNodeManager(settings)
        tts_service = FakeTTSService()

        _queue_conversation_timeout_notice(
            device_id=device_id,
            voice_node_manager=manager,
            tts_service=tts_service,  # type: ignore[arg-type]
            settings=settings,
        )

        first = manager.pop_next_command(device_id=device_id).command
        second = manager.pop_next_command(device_id=device_id).command
        third = manager.pop_next_command(device_id=device_id).command
        fourth = manager.pop_next_command(device_id=device_id).command

        self.assertIsNotNone(tts_service.synthesized_text)
        self.assertEqual(first.type if first else None, "conversation_stop")
        self.assertEqual(second.type if second else None, "play_audio")
        self.assertEqual(
            second.audio_url if second else None,
            "/voice-node/audio/current.wav?token=test-token",
        )
        self.assertEqual(third.type if third else None, "wake_listen_start")
        self.assertIsNone(fourth)


if __name__ == "__main__":
    unittest.main()
