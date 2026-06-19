import unittest
from datetime import datetime, timezone

from server.config import get_settings
from server.models.esp32 import DeviceStatusResponse, HeartbeatRequest
from server.services.assistant_audio_service import AssistantAudioService
from server.services.device_control import DeviceControlService
from server.services.device_registry import DeviceRegistry
from server.services.esp32_manager import Esp32Manager
from server.services.intent_router import IntentRouter
from server.services.voice_node_text_normalizer import normalize_voice_node_transcript


class VoiceNodeIntentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.router = IntentRouter()

    def test_device_control_accepts_common_spoken_phrases(self) -> None:
        phrases = [
            "ช่วยเปิดไฟห้องนั่งเล่นให้หน่อย",
            "ดับไฟห้องนอน",
            "ไฟห้องครัวติดไหม",
            "ไฟห้องน้ำ",
            "เปิดรีเลย์ช่องหนึ่ง",
            "ปิดช่อง 4",
            "เปิดไฟดวงแรก",
            "ปิดไฟตัวสาม",
            "ปิดไฟทั้งหมด",
        ]

        for phrase in phrases:
            with self.subTest(phrase=phrase):
                self.assertEqual(self.router.classify(phrase).intent, "device_control")

    def test_voice_node_normalizer_repairs_wake_and_device_words(self) -> None:
        self.assertEqual(normalize_voice_node_transcript("ตอนน้องฟา"), "ตอนน้องฟ้า")
        self.assertEqual(normalize_voice_node_transcript("สวัสดีน้องฝัน"), "สวัสดีน้องฟ้า")
        self.assertEqual(normalize_voice_node_transcript("เปิดไฟง่าย"), "เปิดไฟให้")
        self.assertEqual(normalize_voice_node_transcript("ห้องนังเล่น"), "ห้องนั่งเล่น")
        self.assertEqual(normalize_voice_node_transcript("เถอะ ไฟ ห้องน้า"), "เปิดไฟ ห้องน้ำ")
        self.assertEqual(normalize_voice_node_transcript("เกิดไฟห้องนั่งเล่น"), "เปิดไฟห้องนั่งเล่น")
        self.assertEqual(normalize_voice_node_transcript("BIT FIRE"), "ปิดไฟ")
        self.assertEqual(normalize_voice_node_transcript("ใคร ห้องน้ำ"), "ไฟ ห้องน้ำ")
        self.assertEqual(normalize_voice_node_transcript("ฝ่อนจัดตกมาย"), "ฝนจะตกไหม")
        self.assertEqual(normalize_voice_node_transcript("อาการร้อน"), "อากาศร้อนไหม")
        self.assertEqual(normalize_voice_node_transcript("ยักล่ารอดติดไหม"), "ยะลารถติดไหม")

    def test_spoken_reply_expands_percent_for_tts(self) -> None:
        self.assertIn(
            "80 เปอร์เซ็นต์",
            AssistantAudioService._normalize_spoken_text("โอกาสฝน 80%"),
        )


class DeviceControlPhraseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = get_settings()

    def test_detect_action_accepts_turn_on_and_turn_off_variants(self) -> None:
        self.assertEqual(DeviceControlService._detect_action("ช่วยติดไฟให้หน่อย"), "on")
        self.assertEqual(DeviceControlService._detect_action("ดับไฟห้องนั่งเล่น"), "off")
        self.assertTrue(DeviceControlService._is_all_relay_request("ปิดไฟทั้งหมด"))

    def test_registry_selects_each_relay_channel_from_spoken_names(self) -> None:
        registry = DeviceRegistry(self.settings)
        cases = {
            "เปิดไฟห้องรับแขก": ("relay_1", 1),
            "เปิดไฟห้องนอน": ("relay_2", 2),
            "ปิดไฟห้องน้ำ": ("relay_3", 3),
            "เปิดไฟห้องครัว": ("relay_4", 4),
            "ปิดไฟตัวสาม": ("relay_3", 3),
            "เปิดช่อง 4": ("relay_4", 4),
            "เปิดรีเลย์ช่องสอง": ("relay_2", 2),
        }

        for phrase, (device_id, channel) in cases.items():
            with self.subTest(phrase=phrase):
                device = registry.find_controllable_device(phrase)
                self.assertIsNotNone(device)
                self.assertEqual(device.id, device_id)
                self.assertEqual(device.relay_channel, channel)

    def test_offline_board_does_not_enqueue_relay_command(self) -> None:
        esp32_manager = Esp32Manager()
        registry = DeviceRegistry(self.settings)
        service = DeviceControlService(
            settings=self.settings,
            esp32_manager=esp32_manager,
            device_registry=registry,
        )

        result = service.handle_message("เปิดไฟห้องนอน", device_id="esp32-01")

        self.assertIn("บอร์ด esp32-01 ยังไม่ออนไลน์", result.reply)
        self.assertNotIn("ส่งคำสั่ง", result.reply)
        self.assertEqual(esp32_manager.get_pending_command_count("esp32-01"), 0)

    def test_online_board_enqueues_selected_relay_channel(self) -> None:
        esp32_manager = Esp32Manager()
        esp32_manager.record_heartbeat(HeartbeatRequest(device_id="esp32-01"))
        registry = DeviceRegistry(self.settings)
        service = DeviceControlService(
            settings=self.settings,
            esp32_manager=esp32_manager,
            device_registry=registry,
        )

        result = service.handle_message("เปิดไฟห้องครัว", device_id="esp32-01")
        command = esp32_manager.get_next_command("esp32-01")

        self.assertIn("ส่งคำสั่งเปิดไฟห้องครัว", result.reply)
        self.assertIsNotNone(command)
        self.assertEqual(command.channel, 4)
        self.assertEqual(command.target_device_id, "relay_4")
        self.assertEqual(command.action, "on")

    def test_all_relay_command_respects_board_online_state(self) -> None:
        offline_manager = Esp32Manager()
        offline_service = DeviceControlService(
            settings=self.settings,
            esp32_manager=offline_manager,
            device_registry=DeviceRegistry(self.settings),
        )

        offline_result = offline_service.handle_message("ปิดไฟทั้งหมด", device_id="esp32-01")

        self.assertIn("บอร์ด esp32-01 ยังไม่ออนไลน์", offline_result.reply)
        self.assertEqual(offline_manager.get_pending_command_count("esp32-01"), 0)

        online_manager = Esp32Manager()
        online_manager.record_heartbeat(HeartbeatRequest(device_id="esp32-01"))
        online_service = DeviceControlService(
            settings=self.settings,
            esp32_manager=online_manager,
            device_registry=DeviceRegistry(self.settings),
        )

        online_result = online_service.handle_message("ปิดไฟทั้งหมด", device_id="esp32-01")
        commands = [online_manager.get_next_command("esp32-01") for _ in range(4)]

        self.assertIn("ส่งคำสั่งปิดไฟทั้งหมด 4 จุด", online_result.reply)
        self.assertEqual([command.channel for command in commands], [1, 2, 3, 4])
        self.assertEqual([command.action for command in commands], ["off"] * 4)

    def test_specific_device_without_action_stays_in_device_control(self) -> None:
        esp32_manager = Esp32Manager()
        registry = DeviceRegistry(self.settings)
        service = DeviceControlService(
            settings=self.settings,
            esp32_manager=esp32_manager,
            device_registry=registry,
        )

        self.assertEqual(IntentRouter().classify("ไฟห้องน้ำ").intent, "device_control")
        result = service.handle_message("ไฟห้องน้ำ", device_id="esp32-01")

        self.assertIn("เจอไฟห้องน้ำแล้ว", result.reply)
        self.assertIn("บอร์ด esp32-01 ยังไม่ออนไลน์", result.reply)

    def test_status_reply_includes_real_board_online_state(self) -> None:
        online_status = DeviceStatusResponse(
            device_id="esp32-01",
            online=True,
            last_seen_at=datetime.now(timezone.utc),
            seconds_since_heartbeat=1,
        )
        offline_status = DeviceStatusResponse(
            device_id="esp32-01",
            online=False,
            last_seen_at=datetime.now(timezone.utc),
            seconds_since_heartbeat=99,
        )

        online_reply = DeviceControlService._build_status_reply(
            spoken_name="ไฟห้องรับแขก",
            state="on",
            command_status="applied",
            esp32_device_id="esp32-01",
            board_status=online_status,
        )
        offline_reply = DeviceControlService._build_status_reply(
            spoken_name="ไฟห้องรับแขก",
            state="on",
            command_status="applied",
            esp32_device_id="esp32-01",
            board_status=offline_status,
        )

        self.assertIn("บอร์ด esp32-01 ออนไลน์", online_reply)
        self.assertIn("ไฟห้องรับแขกเปิดอยู่", online_reply)
        self.assertIn("บอร์ด esp32-01 ออฟไลน์", offline_reply)
        self.assertIn("ยืนยันสถานะจริงไม่ได้", offline_reply)


if __name__ == "__main__":
    unittest.main()
