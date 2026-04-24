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
    "weather_query": "รับคำถามเรื่องอากาศแล้ว เดี๋ยวจะเชื่อมข้อมูลสดในขั้นถัดไป",
    "traffic_query": "รับคำถามเรื่องการจราจรแล้ว เดี๋ยวจะเชื่อมข้อมูลจริงในขั้นถัดไป",
    "sensor_query": "รับคำถามจากข้อมูลในบ้านแล้ว เดี๋ยวจะเชื่อมเซนเซอร์จริงในขั้นถัดไป",
}


class IntentRouter:
    """Fast rule-based intent classifier for Thai smart-home messages."""

    def __init__(self, rules: Sequence[KeywordRule] | None = None) -> None:
        self._rules = tuple(rules or DEFAULT_RULES)

    def classify(self, message: str) -> IntentMatch:
        normalized_message = self._normalize(message)
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

    @staticmethod
    def _normalize(text: str) -> str:
        return "".join(text.casefold().split())


DEFAULT_RULES: tuple[KeywordRule, ...] = (
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
            "ใช้เวลากี่นาที",
            "ไปตลาด",
            "ไปทำงาน",
            "เส้นทาง",
            "ถนน",
        ),
    ),
)


def get_intent_router() -> IntentRouter:
    return IntentRouter()
