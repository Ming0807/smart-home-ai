import unittest

from server.services.assistant_audio_service import AssistantAudioService


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

    def test_wake_mode_direct_command_is_meaningful(self) -> None:
        self.assertTrue(
            AssistantAudioService._is_meaningful_wake_direct_command(
                "\u0e27\u0e31\u0e19\u0e19\u0e35\u0e49\u0e1d\u0e19\u0e08\u0e30\u0e15\u0e01\u0e44\u0e2b\u0e21"
            )
        )

    def test_wake_mode_greeting_without_wake_word_stays_silent(self) -> None:
        self.assertFalse(
            AssistantAudioService._is_meaningful_wake_direct_command(
                "\u0e2a\u0e27\u0e31\u0e2a\u0e14\u0e35"
            )
        )


if __name__ == "__main__":
    unittest.main()
