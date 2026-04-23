from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Literal

import requests
from requests import Response
from requests.exceptions import RequestException, Timeout

from server.config import Settings, get_settings

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "คุณคือผู้ช่วย AI บ้านอัจฉริยะที่คุยภาษาไทยอย่างเป็นธรรมชาติ "
    "ตอบให้สั้น ชัดเจน เป็นมิตร และอย่าอ้างว่าควบคุมอุปกรณ์จริงจนกว่าระบบจะรองรับ"
)
FALLBACK_REPLY = "ตอนนี้ระบบตอบช้ากว่าปกตินิดนึง ลองใหม่อีกครั้งได้ไหม"


@dataclass(frozen=True)
class LLMResponse:
    reply: str
    model: str
    source: Literal["ollama", "fallback"]
    fallback: bool = False
    error: str | None = None


class LLMManager:
    """Handles local Ollama chat completion calls."""

    def __init__(
        self,
        settings: Settings,
        session: requests.Session | None = None,
    ) -> None:
        self._settings = settings
        self._session = session or requests.Session()

    def generate_reply(self, message: str, stream: bool = False) -> LLMResponse:
        if stream:
            return self._fallback("streaming responses are not enabled yet")

        try:
            response = self._session.post(
                self._chat_url,
                json=self._build_payload(message=message, stream=False),
                timeout=self._settings.ollama_timeout_seconds,
            )
            response.raise_for_status()
            reply = self._parse_chat_response(response)
            return LLMResponse(
                reply=reply,
                model=self._settings.ollama_model,
                source="ollama",
            )
        except Timeout:
            logger.warning("Ollama chat request timed out")
            return self._fallback("ollama timeout")
        except RequestException as exc:
            logger.warning("Ollama chat request failed: %s", self._format_request_error(exc))
            return self._fallback("ollama unavailable")
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Invalid Ollama chat response: %s", exc.__class__.__name__)
            return self._fallback("invalid ollama response")

    def stream_reply(self, message: str) -> Iterator[str]:
        """Yield streamed response chunks for future UI work."""
        with self._session.post(
            self._chat_url,
            json=self._build_payload(message=message, stream=True),
            timeout=self._settings.ollama_timeout_seconds,
            stream=True,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                chunk = json.loads(line)
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content

    @property
    def _chat_url(self) -> str:
        return f"{self._settings.ollama_base_url.rstrip('/')}/api/chat"

    def _build_payload(self, message: str, stream: bool) -> dict[str, Any]:
        return {
            "model": self._settings.ollama_model,
            "messages": [
                {"role": "system", "content": self._load_system_prompt()},
                {"role": "user", "content": message},
            ],
            "stream": stream,
            "options": {
                "temperature": self._settings.llm_temperature,
                "num_predict": self._settings.llm_max_tokens,
            },
        }

    def _load_system_prompt(self) -> str:
        prompt_path = self._resolve_prompt_path(self._settings.system_prompt_path)
        try:
            prompt = prompt_path.read_text(encoding="utf-8").strip()
        except OSError:
            return DEFAULT_SYSTEM_PROMPT
        return prompt or DEFAULT_SYSTEM_PROMPT

    @staticmethod
    def _resolve_prompt_path(prompt_path: str) -> Path:
        path = Path(prompt_path)
        if path.is_absolute():
            return path
        project_root = Path(__file__).resolve().parents[2]
        return project_root / path

    @staticmethod
    def _parse_chat_response(response: Response) -> str:
        payload = response.json()
        reply = payload["message"]["content"].strip()
        if not reply:
            raise ValueError("empty llm reply")
        return reply

    @staticmethod
    def _format_request_error(exc: RequestException) -> str:
        response = exc.response
        if response is None:
            return exc.__class__.__name__
        body = response.text[:500].replace("\n", " ")
        return f"{exc.__class__.__name__} status={response.status_code} body={body}"

    def _fallback(self, error: str) -> LLMResponse:
        return LLMResponse(
            reply=FALLBACK_REPLY,
            model=self._settings.ollama_model,
            source="fallback",
            fallback=True,
            error=error,
        )


def get_llm_manager() -> LLMManager:
    return LLMManager(settings=get_settings())
