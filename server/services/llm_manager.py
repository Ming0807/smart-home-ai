from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Iterator, Literal

import requests
from requests import Response
from requests.exceptions import RequestException, Timeout

from server.config import Settings, get_settings
from server.utils.observability import log_timing, start_timer

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "คุณคือผู้ช่วย AI บ้านอัจฉริยะที่คุยภาษาไทยอย่างเป็นธรรมชาติ "
    "ตอบให้สั้น ชัดเจน เป็นมิตร และอย่าอ้างว่าควบคุมอุปกรณ์จริงจนกว่าระบบจะรองรับ"
)
DEFAULT_FALLBACK_REPLY = "ตอนนี้ระบบตอบช้ากว่าปกตินิดนึง ลองใหม่อีกครั้งได้ไหม"


@dataclass(frozen=True)
class LLMResponse:
    reply: str
    model: str
    source: Literal["ollama", "fallback", "cache"]
    fallback: bool = False
    error: str | None = None


@dataclass(frozen=True)
class CachedLLMResponse:
    response: LLMResponse
    expires_at: datetime


@dataclass(frozen=True)
class LLMHealthStatus:
    available: bool
    model_present: bool
    warmed_up: bool
    source: Literal["live", "cache"]
    checked_at: datetime | None
    last_error: str | None = None
    last_latency_ms: float | None = None


class LLMManager:
    """Handles local Ollama health, warmup, caching, and chat completion calls."""

    def __init__(
        self,
        settings: Settings,
        session: requests.Session | None = None,
    ) -> None:
        self._settings = settings
        self._session = session or requests.Session()
        self._lock = Lock()
        self._health_cache: LLMHealthStatus | None = None
        self._health_expires_at: datetime | None = None
        self._response_cache: dict[str, CachedLLMResponse] = {}
        self._last_error: str | None = None
        self._last_latency_ms: float | None = None
        self._warmed_up = False

    def generate_reply(self, message: str, stream: bool = False) -> LLMResponse:
        if stream:
            return self._fallback("streaming responses are not enabled yet")

        cached_response = self._get_cached_response(message)
        if cached_response is not None:
            return cached_response

        llm_response = self.generate_custom_reply(
            message=message,
            system_prompt=self._load_system_prompt(),
            max_tokens=self._settings.llm_max_tokens,
            temperature=self._settings.llm_temperature,
            log_mode="default",
        )
        if llm_response.source == "ollama":
            self._set_cached_response(message, llm_response)
        return llm_response

    def generate_custom_reply(
        self,
        message: str,
        system_prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        log_mode: str = "custom",
    ) -> LLMResponse:
        if not system_prompt.strip():
            return self._fallback("empty system prompt")

        health_status = self.get_health_status()
        if not health_status.available:
            return self._fallback(health_status.last_error or "ollama unavailable")

        timer = start_timer()
        try:
            response = self._session.post(
                self._chat_url,
                json=self._build_payload(
                    message=message,
                    stream=False,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                ),
                timeout=self._request_timeout_seconds,
            )
            response.raise_for_status()
            reply = self._parse_chat_response(response)
            return LLMResponse(
                reply=reply,
                model=self._settings.ollama_model,
                source="ollama",
            )
        except Timeout:
            self._set_error("ollama timeout")
            logger.warning("Ollama chat request timed out")
            return self._fallback("ollama timeout")
        except RequestException as exc:
            formatted_error = self._format_request_error(exc)
            self._set_error(formatted_error)
            logger.warning("Ollama chat request failed: %s", formatted_error)
            return self._fallback("ollama unavailable")
        except (KeyError, TypeError, ValueError) as exc:
            error = f"invalid ollama response: {exc.__class__.__name__}"
            self._set_error(error)
            logger.warning("Invalid Ollama chat response: %s", exc.__class__.__name__)
            return self._fallback("invalid ollama response")
        finally:
            self._last_latency_ms = timer.elapsed_ms
            log_timing(
                logger,
                self._settings,
                "llm.chat",
                timer.elapsed_ms,
                model=self._settings.ollama_model,
                mode=log_mode,
            )

    def stream_reply(self, message: str) -> Iterator[str]:
        """Yield streamed response chunks for future UI work."""
        with self._session.post(
            self._chat_url,
            json=self._build_payload(message=message, stream=True),
            timeout=self._request_timeout_seconds,
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

    def warmup(self) -> LLMHealthStatus:
        health_status = self.check_health(force_refresh=True)
        if not health_status.available:
            return health_status

        timer = start_timer()
        try:
            response = self._session.post(
                self._chat_url,
                json=self._build_warmup_payload(),
                timeout=min(self._request_timeout_seconds, 15.0),
            )
            response.raise_for_status()
            self._parse_chat_response(response)
            self._warmed_up = True
            self._last_error = None
        except (RequestException, KeyError, TypeError, ValueError) as exc:
            error = (
                self._format_request_error(exc)
                if isinstance(exc, RequestException)
                else f"warmup failed: {exc.__class__.__name__}"
            )
            self._set_error(error)
            logger.warning("LLM warmup failed: %s", error)
        finally:
            self._last_latency_ms = timer.elapsed_ms
            log_timing(
                logger,
                self._settings,
                "llm.warmup",
                timer.elapsed_ms,
                model=self._settings.ollama_model,
            )

        return self.check_health(force_refresh=True)

    def get_health_status(self) -> LLMHealthStatus:
        return self.check_health(force_refresh=False)

    def check_health(self, force_refresh: bool = False) -> LLMHealthStatus:
        with self._lock:
            if not force_refresh and self._health_cache is not None and self._health_expires_at:
                if self._health_expires_at > self._now():
                    return LLMHealthStatus(
                        available=self._health_cache.available,
                        model_present=self._health_cache.model_present,
                        warmed_up=self._health_cache.warmed_up,
                        source="cache",
                        checked_at=self._health_cache.checked_at,
                        last_error=self._health_cache.last_error,
                        last_latency_ms=self._health_cache.last_latency_ms,
                    )

        timer = start_timer()
        available = False
        model_present = False
        checked_at = self._now()
        last_error: str | None = None
        try:
            response = self._session.get(
                self._tags_url,
                timeout=min(self._request_timeout_seconds, 10.0),
            )
            response.raise_for_status()
            payload = response.json()
            models = payload.get("models", [])
            model_names = {
                str(item.get("model", "")).strip()
                for item in models
                if isinstance(item, dict)
            }
            model_present = self._settings.ollama_model in model_names
            available = model_present
            if not model_present:
                last_error = f"model not found: {self._settings.ollama_model}"
        except Timeout:
            last_error = "ollama health timeout"
        except RequestException as exc:
            last_error = self._format_request_error(exc)
        except (TypeError, ValueError, KeyError) as exc:
            last_error = f"invalid ollama health response: {exc.__class__.__name__}"

        health_status = LLMHealthStatus(
            available=available,
            model_present=model_present,
            warmed_up=self._warmed_up and available,
            source="live",
            checked_at=checked_at,
            last_error=last_error or self._last_error,
            last_latency_ms=timer.elapsed_ms,
        )

        with self._lock:
            self._health_cache = health_status
            self._health_expires_at = self._now() + timedelta(
                seconds=self._settings.llm_health_cache_ttl_seconds,
            )
        log_timing(
            logger,
            self._settings,
            "llm.health",
            timer.elapsed_ms,
            available=health_status.available,
            warmed=health_status.warmed_up,
        )
        return health_status

    @property
    def _chat_url(self) -> str:
        return f"{self._settings.ollama_base_url.rstrip('/')}/api/chat"

    @property
    def _tags_url(self) -> str:
        return f"{self._settings.ollama_base_url.rstrip('/')}/api/tags"

    @property
    def _request_timeout_seconds(self) -> float:
        return min(
            self._settings.chat_timeout_seconds,
            self._settings.ollama_timeout_seconds,
        )

    def _build_payload(
        self,
        message: str,
        stream: bool,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        return {
            "model": self._settings.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt or self._load_system_prompt()},
                {"role": "user", "content": message},
            ],
            "stream": stream,
            "options": {
                "temperature": (
                    self._settings.llm_temperature if temperature is None else temperature
                ),
                "num_predict": self._settings.llm_max_tokens if max_tokens is None else max_tokens,
            },
        }

    def _build_warmup_payload(self) -> dict[str, Any]:
        return {
            "model": self._settings.ollama_model,
            "messages": [
                {"role": "system", "content": "ตอบสั้นมากเพื่อ warmup model"},
                {"role": "user", "content": "พร้อมไหม"},
            ],
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": 8,
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
    def _normalize_message(message: str) -> str:
        return " ".join(message.casefold().split())

    def _get_cached_response(self, message: str) -> LLMResponse | None:
        normalized_message = self._normalize_message(message)
        if len(normalized_message) > 120:
            return None

        with self._lock:
            cached = self._response_cache.get(normalized_message)
            if cached is None:
                return None
            if cached.expires_at <= self._now():
                self._response_cache.pop(normalized_message, None)
                return None
            cached_response = cached.response
        return LLMResponse(
            reply=cached_response.reply,
            model=cached_response.model,
            source="cache",
            fallback=cached_response.fallback,
            error=cached_response.error,
        )

    def _set_cached_response(self, message: str, response: LLMResponse) -> None:
        normalized_message = self._normalize_message(message)
        if len(normalized_message) > 120:
            return

        with self._lock:
            if len(self._response_cache) >= 32:
                oldest_key = next(iter(self._response_cache))
                self._response_cache.pop(oldest_key, None)
            self._response_cache[normalized_message] = CachedLLMResponse(
                response=response,
                expires_at=self._now()
                + timedelta(seconds=self._settings.llm_response_cache_ttl_seconds),
            )

    @staticmethod
    def _format_request_error(exc: RequestException) -> str:
        response = exc.response
        if response is None:
            return exc.__class__.__name__
        body = response.text[:500].replace("\n", " ")
        return f"{exc.__class__.__name__} status={response.status_code} body={body}"

    def _fallback(self, error: str) -> LLMResponse:
        self._set_error(error)
        return LLMResponse(
            reply=DEFAULT_FALLBACK_REPLY,
            model=self._settings.ollama_model,
            source="fallback",
            fallback=True,
            error=error,
        )

    def _set_error(self, error: str) -> None:
        self._last_error = error
        with self._lock:
            if self._health_cache is not None:
                self._health_cache = LLMHealthStatus(
                    available=False,
                    model_present=self._health_cache.model_present,
                    warmed_up=False,
                    source="live",
                    checked_at=self._now(),
                    last_error=error,
                    last_latency_ms=self._last_latency_ms,
                )
                self._health_expires_at = self._now() + timedelta(seconds=5)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)


_llm_manager = LLMManager(settings=get_settings())


def get_llm_manager() -> LLMManager:
    return _llm_manager
