from __future__ import annotations

import re


def normalize_voice_node_transcript(text: str) -> str:
    """Correct common Thai STT mistakes before intent routing."""
    cleaned = " ".join(text.split()).strip()
    if not cleaned:
        return cleaned

    corrected = cleaned
    corrected = _normalize_common_particles(corrected)
    corrected = _normalize_wake_words(corrected)
    corrected = _normalize_place_and_traffic_words(corrected)
    corrected = _normalize_weather_words(corrected)
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


def _normalize_wake_words(text: str) -> str:
    corrected = text
    replacements = {
        "สวัดดีน": "สวัสดี",
        "สวัดดี": "สวัสดี",
        "สวัสดีน้ำฝา": "สวัสดีน้องฟ้า",
        "น้ำฝา": "น้องฟ้า",
        "น้องฟา": "น้องฟ้า",
        "น้องฟ่า": "น้องฟ้า",
        "นองฟ้า": "น้องฟ้า",
        "น้องฝ่า": "น้องฟ้า",
        "น้องฝัน": "น้องฟ้า",
        "น้องฟัน": "น้องฟ้า",
        "น้องฟัง": "น้องฟ้า",
        "น้องฟาง": "น้องฟ้า",
    }
    for wrong, right in replacements.items():
        corrected = corrected.replace(wrong, right)
    return corrected


def _normalize_place_and_traffic_words(text: str) -> str:
    corrected = text
    replacements = {
        "กรุ่งเทพ": "กรุงเทพ",
        "กรุงเทบ": "กรุงเทพ",
        "กรุงเทพฯ": "กรุงเทพ",
        "ยาละ": "ยะลา",
        "ยะล่ะ": "ยะลา",
        "ยักล่า": "ยะลา",
        "อยากล่า": "ยะลา",
        "เยลา": "ยะลา",
        "เยล่า": "ยะลา",
        "หาดใหย่": "หาดใหญ่",
        "สนามบีน": "สนามบิน",
        "รอดติด": "รถติด",
        "รู้ดิด": "รถติด",
        "รถดิด": "รถติด",
    }
    for wrong, right in replacements.items():
        corrected = corrected.replace(wrong, right)

    normalized = _compact(corrected)
    if "รดติด" in normalized or "รตติด" in normalized or "รถตืด" in normalized:
        corrected = corrected.replace("รดติด", "รถติด")
        corrected = corrected.replace("รตติด", "รถติด")
        corrected = corrected.replace("รถตืด", "รถติด")
    return corrected


def _normalize_weather_words(text: str) -> str:
    corrected = text
    normalized = _compact(corrected)
    has_rain_context = any(
        keyword in normalized
        for keyword in (
            "ตกไหม",
            "ตกไม่",
            "จะตก",
            "ฝนตก",
            "ฝ่อน",
            "ฝ่น",
            "ฟนตก",
            "โฟนตก",
            "ผมจะตก",
            "จัดตก",
            "วันนี้",
            "อากาศ",
            "อาการ",
            "ร้อน",
        )
    )
    if not has_rain_context:
        return corrected

    replacements = {
        "โฟนจะตกไหม": "ฝนจะตกไหม",
        "โฟนจะตกไม่": "ฝนจะตกไหม",
        "ฟนจะตกไหม": "ฝนจะตกไหม",
        "ฟนจะตกไม่": "ฝนจะตกไหม",
        "ผมจะตกไหม": "ฝนจะตกไหม",
        "ผมจะตกไม่": "ฝนจะตกไหม",
        "โฟนตกไหม": "ฝนตกไหม",
        "โฟนตกไม่": "ฝนตกไหม",
        "ฟนตกไหม": "ฝนตกไหม",
        "ฟนตกไม่": "ฝนตกไหม",
        "ฝนจะตกไม่": "ฝนจะตกไหม",
        "ฝนตกไม่": "ฝนตกไหม",
        "ฝ่อนจัดตกมาย": "ฝนจะตกไหม",
        "ฝ่นจัดตกมาก": "ฝนจะตกไหม",
        "ฝนจัดตกมาก": "ฝนจะตกไหม",
        "ฝนจัดตกมาย": "ฝนจะตกไหม",
        "อาการร้อนมาย": "อากาศร้อนไหม",
        "อาการร้อน": "อากาศร้อนไหม",
        "ผักกาทร้อนมัยมัยมัยนี้": "อากาศร้อนไหมวันนี้",
        "ผักกาทร้อน": "อากาศร้อน",
    }
    for wrong, right in replacements.items():
        corrected = corrected.replace(wrong, right)

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
            "ข่าว",
            "ขาว",
            "ข้าว",
            "หาว",
            "คาว",
            "ล่าสุด",
            "วันนี้",
            "สหรัฐ",
            "อิหร่าน",
            "การเมือง",
            "เทคโนโลยี",
            "ai",
            "เอไอ",
            "line",
            "ไล",
            "ไลน์",
            "หลาย",
            "อานขาว",
            "อ่านขาว",
            "คอที่",
            "คอ ",
            "ขอที่",
        )
    )
    if not has_news_context:
        return corrected

    replacements = {
        "อานขาว": "อ่านข่าว",
        "อ่านขาว": "อ่านข่าว",
        "อานข่าว": "อ่านข่าว",
        "คอที่": "ข้อที่",
        "ขอที่": "ข้อที่",
        "คอ 1": "ข้อ 1",
        "คอ 2": "ข้อ 2",
        "คอ 3": "ข้อ 3",
        "คอ 4": "ข้อ 4",
        "คอ 5": "ข้อ 5",
        "ขอ 1": "ข้อ 1",
        "ขอ 2": "ข้อ 2",
        "ขอ 3": "ข้อ 3",
        "ขอ 4": "ข้อ 4",
        "ขอ 5": "ข้อ 5",
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
        "มีขาวอะไร": "มีข่าวอะไร",
        "มีข้าวอะไร": "มีข่าวอะไร",
        "มีหาวอะไร": "มีข่าวอะไร",
        "มีคาวอะไร": "มีข่าวอะไร",
        "ส่งขาวเข้า": "ส่งข่าวเข้า",
        "ส่งคาวเข้า": "ส่งข่าวเข้า",
        "ส่งหาวเข้า": "ส่งข่าวเข้า",
        "ส่งข่าวเข้าหลาย": "ส่งข่าวเข้าไลน์",
        "ส่งขาวเข้าหลาย": "ส่งข่าวเข้าไลน์",
        "ส่งข้าวเข้าหลาย": "ส่งข่าวเข้าไลน์",
        "ส่งข่าวเข้าไล": "ส่งข่าวเข้าไลน์",
        "ส่งข่าวเข้าไลน์น์": "ส่งข่าวเข้าไลน์",
    }
    for wrong, right in replacements.items():
        corrected = corrected.replace(wrong, right)

    corrected = re.sub(r"^(หาว|คาว|ขาว|ข้าว)(?=.*(ล่าสุด|วันนี้|สหรัฐ|อิหร่าน|อะไร|LINE|ไลน์|หลาย))", "ข่าว", corrected)
    corrected = re.sub(r"(?<=ส่งข่าวเข้า)หลาย", "ไลน์", corrected)
    corrected = re.sub(r"(?<=ส่งข่าวเข้า)ไล(?!น์)", "ไลน์", corrected)
    return corrected


def _normalize_device_words(text: str) -> str:
    corrected = text
    replacements = {
        "BIT FIRE": "ปิดไฟ",
        "Bit Fire": "ปิดไฟ",
        "bit fire": "ปิดไฟ",
        "บิทไฟ": "ปิดไฟ",
        "บิดไฟ": "ปิดไฟ",
        "เกิดไฟ": "เปิดไฟ",
        "เกีดไฟ": "เปิดไฟ",
        "เกินไฟ": "เปิดไฟ",
        "เถอะ ไฟ": "เปิดไฟ",
        "เถอะไฟ": "เปิดไฟ",
        "เถิดไฟ": "เปิดไฟ",
        "เปิด ไฟ": "เปิดไฟ",
        "ปิด ไฟ": "ปิดไฟ",
        "เปิดไฟไง": "เปิดไฟ",
        "ติดไฟให้หน่อย": "เปิดไฟให้หน่อย",
        "ดับฟาย": "ดับไฟ",
        "ดับไฟง่าย": "ดับไฟ",
        "ใคร ห้อง": "ไฟ ห้อง",
        "ใครห้อง": "ไฟห้อง",
        "ห้องน้า": "ห้องน้ำ",
        "ห้องนังเล่น": "ห้องนั่งเล่น",
        "ห้องนั่งเลน": "ห้องนั่งเล่น",
        "รีเล": "รีเลย์",
        "รีเรย์": "รีเลย์",
    }
    for wrong, right in replacements.items():
        corrected = corrected.replace(wrong, right)
    corrected = corrected.replace(
        "\u0e40\u0e1b\u0e34\u0e14\u0e44\u0e1f\u0e07\u0e48\u0e32\u0e22",
        "\u0e40\u0e1b\u0e34\u0e14\u0e44\u0e1f\u0e43\u0e2b\u0e49",
    )
    corrected = corrected.replace(
        "\u0e1b\u0e34\u0e14\u0e44\u0e1f\u0e07\u0e48\u0e32\u0e22",
        "\u0e1b\u0e34\u0e14\u0e44\u0e1f\u0e43\u0e2b\u0e49",
    )
    corrected = corrected.replace(
        "\u0e44\u0e27\u0e49\u0e2b\u0e49\u0e2d\u0e07",
        "\u0e44\u0e1f\u0e2b\u0e49\u0e2d\u0e07",
    )
    corrected = corrected.replace("เปีดไฟ", "เปิดไฟ")
    corrected = corrected.replace("เปิดฟาย", "เปิดไฟ")
    corrected = corrected.replace("ปิดฟาย", "ปิดไฟ")
    corrected = corrected.replace("ปีดไฟ", "ปิดไฟ")
    return corrected


def _compact(text: str) -> str:
    return "".join(text.casefold().split())
