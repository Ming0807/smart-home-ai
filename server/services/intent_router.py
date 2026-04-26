from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from server.models.chat import IntentName


@dataclass(frozen=True)
class IntentMatch:
    intent: IntentName
    matched_keyword: str | None = None


@dataclass(frozen=True)
class PlaceholderResponse:
    reply: str
    intent: IntentName
    source: str = "placeholder"


@dataclass(frozen=True)
class KeywordRule:
    intent: IntentName
    keywords: Sequence[str]


PLACEHOLDER_REPLIES: dict[IntentName, str] = {
    "device_control": "รับคำสั่งควบคุมอุปกรณ์แล้ว เดี๋ยวจะเชื่อมกับอุปกรณ์จริงในขั้นถัดไป",
    "traffic_query": "รับคำถามเรื่องการจราจรแล้ว เดี๋ยวจะเชื่อมข้อมูลจริงในขั้นถัดไป",
    "sensor_query": "รับคำถามจากข้อมูลในบ้านแล้ว เดี๋ยวจะเชื่อมเซนเซอร์จริงในขั้นถัดไป",
}


class IntentRouter:
    """Fast rule-based intent classifier for Thai smart-home messages."""

    _NAVIGATION_PLACE_HINTS = (
        "สนามบิน",
        "airport",
        "ตลาด",
        "market",
        "โรงพยาบาล",
        "hospital",
        "มหาลัย",
        "มหาวิทยาลัย",
        "university",
        "หาดใหญ่",
        "hatyai",
        "hat yai",
    )
    _MOTION_QUERY_PATTERNS = (
        re.compile(r"มีคน(เดินผ่าน|อยู่)?ไหม"),
        re.compile(r"ตรวจเจอคนไหม"),
        re.compile(r"motion\s*ล่าสุด(เมื่อไหร่)?", re.IGNORECASE),
        re.compile(r"มีการเคลื่อนไหวไหม"),
    )
    _NEWS_DETAIL_PATTERNS = (
        re.compile(r"ข้อ\s*[1-9]"),
        re.compile(r"ข่าวข้อ\s*[1-9]"),
        re.compile(r"(เล่าข่าว|อ่านข่าว|รายละเอียดข่าว)\s*ข้อ?\s*[1-9]"),
    )
    _NAVIGATION_PATTERNS = (
        re.compile(r"จาก.+ไป.+(กี่นาที|กี่กิโล|กี่กิโลเมตร|ทางไหนดี|เส้นทาง)", re.IGNORECASE),
        re.compile(r"ไป.+(กี่นาที|กี่กิโล|กี่กิโลเมตร|ทางไหนดี)", re.IGNORECASE),
        re.compile(r"(เส้นทางไป|เดินทางไป).+", re.IGNORECASE),
        re.compile(r"(how\s+long\s+to|route\s+to|directions).+", re.IGNORECASE),
    )

    def __init__(self, rules: Sequence[KeywordRule] | None = None) -> None:
        self._rules = tuple(rules or DEFAULT_RULES)

    def classify(self, message: str) -> IntentMatch:
        normalized_message = self._normalize(message)

        news_detail_match = self._match_news_detail(message, normalized_message)
        if news_detail_match is not None:
            return news_detail_match

        traffic_match = self._match_traffic(message, normalized_message)
        if traffic_match is not None:
            return traffic_match

        motion_match = self._match_motion(message, normalized_message)
        if motion_match is not None:
            return motion_match

        navigation_match = self._match_navigation(message, normalized_message)
        if navigation_match is not None:
            return navigation_match

        for rule in self._rules:
            for keyword in rule.keywords:
                normalized_keyword = self._normalize(keyword)
                if normalized_keyword in normalized_message:
                    return IntentMatch(
                        intent=rule.intent,
                        matched_keyword=keyword,
                    )
        return IntentMatch(intent="general_chat")

    def get_placeholder_response(self, intent: IntentName) -> PlaceholderResponse | None:
        reply = PLACEHOLDER_REPLIES.get(intent)
        if reply is None:
            return None
        return PlaceholderResponse(reply=reply, intent=intent)

    def _match_news_detail(
        self,
        original_message: str,
        normalized_message: str,
    ) -> IntentMatch | None:
        if "ข่าว" not in normalized_message and not normalized_message.startswith("ข้อ"):
            return None

        for pattern in self._NEWS_DETAIL_PATTERNS:
            match = pattern.search(original_message.casefold())
            if match is not None:
                return IntentMatch(
                    intent="news_detail_query",
                    matched_keyword=match.group(0),
                )
        return None

    def _match_navigation(
        self,
        original_message: str,
        normalized_message: str,
    ) -> IntentMatch | None:
        for pattern in self._NAVIGATION_PATTERNS:
            match = pattern.search(original_message.casefold())
            if match is not None:
                return IntentMatch(
                    intent="navigation_query",
                    matched_keyword=match.group(0),
                )

        if normalized_message.startswith("ไป") and any(
            keyword in normalized_message
            for keyword in (
                *self._NAVIGATION_PLACE_HINTS,
                "ยะลา",
            )
        ):
            return IntentMatch(intent="navigation_query", matched_keyword="ไป")

        if any(keyword in normalized_message for keyword in self._NAVIGATION_PLACE_HINTS):
            if any(
                marker in normalized_message
                for marker in ("ล่ะ", "ละ", "ไหม", "กี่นาที", "กี่กิโล", "ทางไหนดี")
            ):
                return IntentMatch(intent="navigation_query", matched_keyword="place_followup")

        if "เส้นทาง" in normalized_message or "directions" in normalized_message:
            return IntentMatch(intent="navigation_query", matched_keyword="เส้นทาง")
        return None

    def _match_traffic(
        self,
        original_message: str,
        normalized_message: str,
    ) -> IntentMatch | None:
        if not any(keyword in normalized_message for keyword in ("รถติด", "การจราจร", "จราจร")):
            return None

        if any(
            keyword in normalized_message
            for keyword in (
                "ไป",
                "จาก",
                "สนามบิน",
                "ตลาด",
                "โรงพยาบาล",
                "มหาลัย",
                "มหาวิทยาลัย",
                "หาดใหญ่",
                "ยะลา",
                "raman",
                "รามัน",
            )
        ):
            return IntentMatch(intent="traffic_query", matched_keyword="traffic_route")

        return IntentMatch(intent="traffic_query", matched_keyword=original_message.strip())

    def _match_motion(
        self,
        original_message: str,
        normalized_message: str,
    ) -> IntentMatch | None:
        for pattern in self._MOTION_QUERY_PATTERNS:
            match = pattern.search(original_message.casefold())
            if match is not None:
                return IntentMatch(
                    intent="sensor_query",
                    matched_keyword=match.group(0),
                )

        if "คน" in normalized_message and "ไหม" in normalized_message:
            return IntentMatch(intent="sensor_query", matched_keyword="motion_people")
        return None

    @staticmethod
    def _normalize(text: str) -> str:
        return "".join(text.casefold().split())


DEFAULT_RULES: tuple[KeywordRule, ...] = (
    KeywordRule(
        intent="news_query",
        keywords=(
            "ข่าววันนี้",
            "ข่าวล่าสุด",
            "ข่าวเทคโนโลยี",
            "ข่าว ai",
            "ข่าวa i",
            "ข่าว",
            "news",
            "latest news",
        ),
    ),
    KeywordRule(
        intent="system_status",
        keywords=(
            "เชื่อมต่อ",
            "เชื่อต่อ",
            "ออนไลน์",
            "online",
            "iot",
            "esp32",
            "บอร์ด",
            "ตรวจสอบระบบ",
        ),
    ),
    KeywordRule(
        intent="device_control",
        keywords=(
            "เปิดไฟ",
            "ปิดไฟ",
            "เปิดพัดลม",
            "ปิดพัดลม",
            "เปิดแอร์",
            "ปิดแอร์",
            "เปิดปลั๊ก",
            "ปิดปลั๊ก",
            "เปิดรีเลย์",
            "ปิดรีเลย์",
        ),
    ),
    KeywordRule(
        intent="sensor_query",
        keywords=(
            "ห้องร้อนไหม",
            "ในห้องร้อนไหม",
            "ตอนนี้กี่องศา",
            "กี่องศา",
            "อุณหภูมิห้อง",
            "อุณหภูมิในห้อง",
            "ความชื้น",
            "เซนเซอร์",
            "มีคนอยู่ไหม",
            "มีการเคลื่อนไหวไหม",
        ),
    ),
    KeywordRule(
        intent="weather_query",
        keywords=(
            "ฝน",
            "อากาศ",
            "ข้างนอกร้อนไหม",
            "ข้างนอกเย็น",
            "ข้างนอกหนาว",
            "ข้างนอกเป็นยังไง",
            "พยากรณ์",
            "แดด",
        ),
    ),
    KeywordRule(
        intent="traffic_query",
        keywords=(
            "รถติด",
            "การจราจร",
            "จราจร",
            "ถนน",
        ),
    ),
)


def get_intent_router() -> IntentRouter:
    return IntentRouter()
