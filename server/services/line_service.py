from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

import requests
from requests.exceptions import RequestException, Timeout

from server.config import Settings, get_settings
from server.services.news_service import NewsItem
from server.utils.observability import log_timing, start_timer

logger = logging.getLogger(__name__)

LINE_PUSH_MESSAGE_URL = "https://api.line.me/v2/bot/message/push"
LINE_NOT_CONFIGURED_REPLY = (
    "ยังไม่ได้ตั้งค่า LINE Messaging API ให้พร้อมส่งลิงก์ข่าว "
    "เพิ่ม LINE_CHANNEL_ACCESS_TOKEN และ LINE_TARGET_ID ใน .env ก่อนนะ"
)
LINE_SEND_FAILED_REPLY = "ส่งลิงก์ข่าวเข้า LINE ไม่สำเร็จ ลองเช็ก token หรือ target id อีกครั้งนะ"


@dataclass(frozen=True)
class LineSendResult:
    reply: str
    source: Literal["line", "fallback"]
    sent: bool
    error: str | None = None


class LineService:
    """Small LINE Messaging API client for demo notifications."""

    def __init__(
        self,
        settings: Settings,
        session: requests.Session | None = None,
    ) -> None:
        self._settings = settings
        self._session = session or requests.Session()

    def send_news_links(
        self,
        *,
        label: str,
        items: tuple[NewsItem, ...],
    ) -> LineSendResult:
        if not items:
            return LineSendResult(
                reply="ยังไม่มีลิงก์ข่าวล่าสุดให้ส่ง ลองถามข่าวก่อนแล้วค่อยสั่งส่งเข้า LINE นะ",
                source="fallback",
                sent=False,
                error="no news items",
            )

        text = self._format_news_message(label=label, items=items)
        return self.send_text(text, success_reply="ส่งลิงก์ข่าวเข้า LINE ให้แล้วนะ")

    def send_text(self, text: str, success_reply: str) -> LineSendResult:
        if not self._settings.line_enabled:
            return LineSendResult(
                reply=LINE_NOT_CONFIGURED_REPLY,
                source="fallback",
                sent=False,
                error="line disabled",
            )
        if not self._settings.line_channel_access_token or not self._settings.line_target_id:
            return LineSendResult(
                reply=LINE_NOT_CONFIGURED_REPLY,
                source="fallback",
                sent=False,
                error="missing line config",
            )

        timer = start_timer()
        try:
            response = self._session.post(
                LINE_PUSH_MESSAGE_URL,
                headers={
                    "Authorization": f"Bearer {self._settings.line_channel_access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "to": self._settings.line_target_id,
                    "messages": [{"type": "text", "text": text[:5000]}],
                },
                timeout=self._settings.line_timeout_seconds,
            )
            response.raise_for_status()
        except Timeout:
            logger.warning("LINE push message timed out")
            return LineSendResult(
                reply=LINE_SEND_FAILED_REPLY,
                source="fallback",
                sent=False,
                error="timeout",
            )
        except RequestException as exc:
            logger.warning("LINE push message failed: %s", self._format_request_error(exc))
            return LineSendResult(
                reply=LINE_SEND_FAILED_REPLY,
                source="fallback",
                sent=False,
                error=exc.__class__.__name__,
            )

        log_timing(
            logger,
            self._settings,
            "line.push",
            timer.elapsed_ms,
            items="news",
        )
        return LineSendResult(reply=success_reply, source="line", sent=True)

    @staticmethod
    def _format_news_message(label: str, items: tuple[NewsItem, ...]) -> str:
        lines = [f"{label}", ""]
        for index, item in enumerate(items, start=1):
            source = f" ({item.source})" if item.source else ""
            lines.append(f"{index}. {item.title}{source}")
            lines.append(item.url)
            if index != len(items):
                lines.append("")
        return "\n".join(lines).strip()

    @staticmethod
    def _format_request_error(exc: RequestException) -> str:
        response = exc.response
        if response is None:
            return exc.__class__.__name__
        body = response.text[:300].replace("\n", " ")
        return f"{exc.__class__.__name__} status={response.status_code} body={body}"


_line_service = LineService(settings=get_settings())


def get_line_service() -> LineService:
    return _line_service
