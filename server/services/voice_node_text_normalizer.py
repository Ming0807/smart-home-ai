from __future__ import annotations

import re


def normalize_voice_node_transcript(text: str) -> str:
    """Correct common INMP441/Faster-Whisper Thai mistakes before intent routing.

    This is intentionally used only for the ESP32-S3 Voice Node path. Browser mic
    keeps its existing browser SpeechRecognition behavior.
    """
    cleaned = " ".join(text.split()).strip()
    if not cleaned:
        return cleaned

    corrected = cleaned
    corrected = _normalize_common_particles(corrected)
    corrected = _normalize_place_and_traffic_words(corrected)
    corrected = _normalize_sensor_words(corrected)
    corrected = _normalize_news_words(corrected)
    corrected = _normalize_device_words(corrected)
    return " ".join(corrected.split()).strip()


def _normalize_common_particles(text: str) -> str:
    corrected = text
    corrected = corrected.replace("มั้ย", "ไหม")
    corrected = corrected.replace("เท่าไร", "เท่าไหร่")
    corrected = corrected.replace("ให้น้อย", "ให้หน่อย")
    return corrected


def _normalize_place_and_traffic_words(text: str) -> str:
    corrected = text
    replacements = {
        "กรุ่งเทพ": "กรุงเทพ",
        "กรุงเทบ": "กรุงเทพ",
        "กรุงเทพฯ": "กรุงเทพ",
        "ยาละ": "ยะลา",
        "ยะล่ะ": "ยะลา",
        "หาดใหย่": "หาดใหญ่",
        "สนามบีน": "สนามบิน",
    }
    for wrong, right in replacements.items():
        corrected = corrected.replace(wrong, right)

    normalized = _compact(corrected)
    if "รดติด" in normalized or "รตติด" in normalized or "รถตืด" in normalized:
        corrected = corrected.replace("รดติด", "รถติด")
        corrected = corrected.replace("รตติด", "รถติด")
        corrected = corrected.replace("รถตืด", "รถติด")
    return corrected


def _normalize_sensor_words(text: str) -> str:
    corrected = text
    corrected = corrected.replace("ความชื่น", "ความชื้น")
    corrected = corrected.replace("ความชื่นเท่าไหร่", "ความชื้นเท่าไหร่")
    corrected = corrected.replace("ความชื่นเท่าไร", "ความชื้นเท่าไหร่")

    normalized = _compact(corrected)
    hot_room_variants = (
        "มองร้อนไหม",
        "มองร้อนไหม",
        "มองร้อนมั้ย",
        "หองร้อนไหม",
        "ห้องร้อนมั้ย",
    )
    if any(variant in normalized for variant in hot_room_variants):
        return "ห้องร้อนไหม"

    return corrected


def _normalize_news_words(text: str) -> str:
    corrected = text
    normalized = _compact(corrected)
    has_news_context = any(
        keyword in normalized
        for keyword in (
            "ล่าสุด",
            "วันนี้",
            "สหรัฐ",
            "อิหร่าน",
            "การเมือง",
            "เทคโนโลยี",
            "ai",
            "เอไอ",
            "line",
            "ไลน์",
        )
    )
    if not has_news_context:
        return corrected

    replacements = {
        "หาวล่าสุด": "ข่าวล่าสุด",
        "คาวล่าสุด": "ข่าวล่าสุด",
        "ขาวล่าสุด": "ข่าวล่าสุด",
        "หาววันนี้": "ข่าววันนี้",
        "คาววันนี้": "ข่าววันนี้",
        "ขาววันนี้": "ข่าววันนี้",
        "หาวสหรัฐ": "ข่าวสหรัฐ",
        "คาวสหรัฐ": "ข่าวสหรัฐ",
        "ขาวสหรัฐ": "ข่าวสหรัฐ",
        "หาวอิหร่าน": "ข่าวอิหร่าน",
        "คาวอิหร่าน": "ข่าวอิหร่าน",
        "ขาวอิหร่าน": "ข่าวอิหร่าน",
        "ส่งข้าวเข้า": "ส่งข่าวเข้า",
        "ข้าวล่าสุด": "ข่าวล่าสุด",
        "ข้าววันนี้": "ข่าววันนี้",
        "ข้าวสหรัฐ": "ข่าวสหรัฐ",
        "ข้าวอิหร่าน": "ข่าวอิหร่าน",
    }
    for wrong, right in replacements.items():
        corrected = corrected.replace(wrong, right)

    corrected = re.sub(r"^(หาว|คาว|ขาว)(?=.*(ล่าสุด|วันนี้|สหรัฐ|อิหร่าน))", "ข่าว", corrected)
    return corrected


def _normalize_device_words(text: str) -> str:
    corrected = text
    corrected = corrected.replace("เปีดไฟ", "เปิดไฟ")
    corrected = corrected.replace("เปิดฟาย", "เปิดไฟ")
    corrected = corrected.replace("ปิดฟาย", "ปิดไฟ")
    corrected = corrected.replace("ปีดไฟ", "ปิดไฟ")
    return corrected


def _compact(text: str) -> str:
    return "".join(text.casefold().split())
