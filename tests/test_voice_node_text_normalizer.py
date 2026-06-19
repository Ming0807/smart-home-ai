import unittest

from server.services.voice_node_text_normalizer import normalize_voice_node_transcript


class VoiceNodeTextNormalizerTest(unittest.TestCase):
    def test_open_light_easy_is_normalized_to_open_light_for_me(self) -> None:
        self.assertEqual(
            normalize_voice_node_transcript(
                "\u0e40\u0e1b\u0e34\u0e14\u0e44\u0e1f\u0e07\u0e48\u0e32\u0e22"
            ),
            "\u0e40\u0e1b\u0e34\u0e14\u0e44\u0e1f\u0e43\u0e2b\u0e49",
        )

    def test_wai_room_is_normalized_to_light_room(self) -> None:
        self.assertEqual(
            normalize_voice_node_transcript(
                "\u0e44\u0e27\u0e49\u0e2b\u0e49\u0e2d\u0e07\u0e19\u0e2d\u0e19\u0e43\u0e2b\u0e49\u0e2b\u0e19\u0e48\u0e2d\u0e22"
            ),
            "\u0e44\u0e1f\u0e2b\u0e49\u0e2d\u0e07\u0e19\u0e2d\u0e19\u0e43\u0e2b\u0e49\u0e2b\u0e19\u0e48\u0e2d\u0e22",
        )


if __name__ == "__main__":
    unittest.main()
