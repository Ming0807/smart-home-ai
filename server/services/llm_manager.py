from __future__ import annotations

import json
import logging
import re
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
DEFAULT_FALLBACK_REPLY = "ตอนนี้โมเดลหลักยังตอบไม่ทัน ลองถามใหม่อีกครั้งหรือถามให้สั้นลงนิดหนึ่งได้ไหม"
GENERAL_CHAT_DEMO_RULES = (
    "\n\nกติกาเดโมสำหรับคำถามทั่วไป:"
    "\n- ตอบภาษาไทยเป็น 1 ประโยคสั้น ๆ ไม่เกิน 25 คำ"
    "\n- ห้ามใช้ bullet, markdown, หรือลิสต์ยาว"
    "\n- ตอบให้จบในตัวเอง ไม่ต้องถามต่อท้าย"
)
THINKING_TRIGGER_PHRASES = (
    "คิดก่อนตอบ",
    "คิดก่อน",
    "วิเคราะห์ก่อน",
    "ขอคิดละเอียด",
    "คิดให้ละเอียด",
    "ขอวิเคราะห์",
    "deep think",
    "think carefully",
)
DEEP_THINK_GENERAL_RULES = (
    "\n\nโหมดคิดก่อนตอบ:"
    "\n- คิดอย่างรอบคอบภายใน แต่ตอบเฉพาะคำตอบสุดท้ายเท่านั้น"
    "\n- ห้ามแสดงขั้นตอนคิดหรือข้อความ JSON"
    "\n- ตอบภาษาไทยชัดเจน กระชับ และเป็นธรรมชาติ"
    "\n- ถ้าคำถามซับซ้อน ให้ตอบเป็นย่อหน้าสั้น ๆ ไม่เกิน 4 ประโยค"
)


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
        self._ollama_request_lock = Lock()
        self._health_cache: LLMHealthStatus | None = None
        self._health_expires_at: datetime | None = None
        self._response_cache: dict[str, CachedLLMResponse] = {}
        self._last_error: str | None = None
        self._last_latency_ms: float | None = None
        self._warmed_up = False
        self._keep_awake_paused = False

    def generate_reply(self, message: str, stream: bool = False) -> LLMResponse:
        if stream:
            return self._fallback("streaming responses are not enabled yet")

        use_thinking = self.is_thinking_request(message)
        prepared_message = (
            self.strip_thinking_trigger(message) if use_thinking else message
        )

        if not use_thinking:
            cached_response = self._get_cached_response(message)
            if cached_response is not None:
                return cached_response

        llm_response = self.generate_custom_reply(
            message=prepared_message,
            system_prompt=(
                self._load_deep_think_general_prompt()
                if use_thinking
                else self._load_general_chat_prompt()
            ),
            max_tokens=(
                self._settings.llm_thinking_max_tokens
                if use_thinking
                else min(
                    self._settings.llm_max_tokens,
                    self._settings.llm_general_max_tokens,
                )
            ),
            temperature=(
                min(self._settings.llm_temperature, 0.15)
                if use_thinking
                else min(self._settings.llm_temperature, 0.2)
            ),
            log_mode="thinking" if use_thinking else "default",
            think=use_thinking,
        )
        if not use_thinking and llm_response.source == "ollama":
            self._set_cached_response(message, llm_response)
        return llm_response

    def generate_custom_reply(
        self,
        message: str,
        system_prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        log_mode: str = "custom",
        think: bool | None = None,
    ) -> LLMResponse:
        if not system_prompt.strip():
            return self._fallback("empty system prompt")

        self._resume_keep_awake()

        health_status = self.get_health_status()
        if not health_status.available:
            logger.info("LLM not available, attempting auto-warmup before reply")
            health_status = self.warmup()
            if not health_status.available:
                return self._fallback(
                    health_status.last_error or "ollama unavailable",
                    mark_unavailable=False,
                )

        timer = start_timer()
        self._acquire_ollama_request(blocking=True, purpose=f"chat:{log_mode}")
        try:
            response = self._session.post(
                self._chat_url,
                json=self._build_payload(
                    message=message,
                    stream=False,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    think=think,
                ),
                timeout=self._request_timeout_seconds,
            )
            response.raise_for_status()
            reply = self._parse_chat_response(response)
            self._warmed_up = True
            return LLMResponse(
                reply=reply,
                model=self._settings.ollama_model,
                source="ollama",
            )
        except Timeout:
            logger.warning("Ollama chat request timed out")
            return self._fallback("ollama timeout", mark_unavailable=False)
        except RequestException as exc:
            formatted_error = self._format_request_error(exc)
            logger.warning("Ollama chat request failed: %s", formatted_error)
            return self._fallback(formatted_error, mark_unavailable=True)
        except (KeyError, TypeError, ValueError) as exc:
            error = f"invalid ollama response: {exc.__class__.__name__}"
            logger.warning("Invalid Ollama chat response: %s", exc.__class__.__name__)
            return self._fallback(error, mark_unavailable=False)
        finally:
            self._last_latency_ms = timer.elapsed_ms
            self._release_ollama_request()
            log_timing(
                logger,
                self._settings,
                "llm.chat",
                timer.elapsed_ms,
                model=self._settings.ollama_model,
                mode=log_mode,
            )

    def stream_reply(self, message: str) -> Iterator[str]:
        """Yield streamed response chunks from Ollama for general chat."""
        self._resume_keep_awake()

        health_status = self.get_health_status()
        if not health_status.available:
            logger.info("LLM not available, attempting auto-warmup before stream")
            health_status = self.warmup()
            if not health_status.available:
                raise RuntimeError(health_status.last_error or "ollama unavailable")

        timer = start_timer()
        self._acquire_ollama_request(blocking=True, purpose="chat.stream")
        try:
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
        finally:
            self._last_latency_ms = timer.elapsed_ms
            self._release_ollama_request()
            log_timing(
                logger,
                self._settings,
                "llm.chat.stream",
                timer.elapsed_ms,
                model=self._settings.ollama_model,
            )

    def warmup(self, blocking: bool = True) -> LLMHealthStatus:
        with self._lock:
            self._keep_awake_paused = False

        health_status = self.check_health(force_refresh=True)
        if not health_status.available:
            return health_status

        if not self._acquire_ollama_request(blocking=blocking, purpose="warmup"):
            return self.get_health_status()

        timer = start_timer()
        try:
            response = self._session.post(
                self._chat_url,
                json=self._build_warmup_payload(),
                timeout=self._warmup_timeout_seconds,
            )
            response.raise_for_status()
            self._parse_chat_response(response)
            self._warmed_up = True
            self._last_error = None
        except Timeout:
            logger.warning("LLM warmup timed out (Ollama might be busy)")
            self._set_error("warmup timeout", mark_unavailable=False)
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
            self._release_ollama_request()
            log_timing(
                logger,
                self._settings,
                "llm.warmup",
                timer.elapsed_ms,
                model=self._settings.ollama_model,
            )

        return self.check_health(force_refresh=True)

    def sleep(self) -> LLMHealthStatus:
        with self._lock:
            self._keep_awake_paused = True
            self._warmed_up = False

        timer = start_timer()
        self._acquire_ollama_request(blocking=True, purpose="sleep")
        try:
            response = self._session.post(
                self._generate_url,
                json={
                    "model": self._settings.ollama_model,
                    "prompt": "",
                    "stream": False,
                    "keep_alive": 0,
                },
                timeout=min(self._request_timeout_seconds, 15.0),
            )
            response.raise_for_status()
            self._last_error = None
        except RequestException as exc:
            error = self._format_request_error(exc)
            self._set_error(error, mark_unavailable=False)
            logger.warning("LLM sleep request failed: %s", error)
        finally:
            self._last_latency_ms = timer.elapsed_ms
            self._release_ollama_request()
            log_timing(
                logger,
                self._settings,
                "llm.sleep",
                timer.elapsed_ms,
                model=self._settings.ollama_model,
            )

        return self.check_health(force_refresh=True)

    def keep_awake_once(self) -> LLMHealthStatus:
        if self.is_keep_awake_paused:
            return self.get_health_status()
        return self.touch_keep_alive(blocking=False)

    def touch_keep_alive(self, blocking: bool = True) -> LLMHealthStatus:
        if not self._acquire_ollama_request(blocking=blocking, purpose="keep_alive"):
            return self.get_health_status()

        timer = start_timer()
        try:
            response = self._session.post(
                self._generate_url,
                json={
                    "model": self._settings.ollama_model,
                    "prompt": "",
                    "stream": False,
                    "keep_alive": self._parsed_keep_alive,
                    "options": {"num_predict": 0},
                },
                timeout=min(self._request_timeout_seconds, 15.0),
            )
            response.raise_for_status()
            self._warmed_up = True
            self._last_error = None
        except Timeout:
            logger.warning("LLM keep-alive touch timed out")
            self._set_error("keep-alive timeout", mark_unavailable=False)
        except RequestException as exc:
            error = self._format_request_error(exc)
            self._set_error(error, mark_unavailable=False)
            logger.warning("LLM keep-alive touch failed: %s", error)
        finally:
            self._last_latency_ms = timer.elapsed_ms
            self._release_ollama_request()
            log_timing(
                logger,
                self._settings,
                "llm.keep_alive",
                timer.elapsed_ms,
                model=self._settings.ollama_model,
            )

        return self.check_health(force_refresh=True)

    @property
    def is_keep_awake_paused(self) -> bool:
        with self._lock:
            return self._keep_awake_paused

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
            previous_available = (
                self._health_cache.available if self._health_cache is not None else False
            )

        timer = start_timer()
        available = False
        model_present = False
        checked_at = self._now()
        last_error: str | None = None
        check_failed = False
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
            check_failed = True
        except RequestException as exc:
            last_error = self._format_request_error(exc)
            check_failed = True
        except (TypeError, ValueError, KeyError) as exc:
            last_error = f"invalid ollama health response: {exc.__class__.__name__}"
            check_failed = True

        # Preserve available status on transient failures (Ollama busy generating)
        if check_failed and previous_available:
            available = True
            model_present = True

        health_status = LLMHealthStatus(
            available=available,
            model_present=model_present,
            warmed_up=self._warmed_up and available,
            source="live",
            checked_at=checked_at,
            last_error=last_error or self._last_error,
            last_latency_ms=timer.elapsed_ms,
        )

        cache_ttl = (
            60 if check_failed
            else self._settings.llm_health_cache_ttl_seconds
        )
        with self._lock:
            self._health_cache = health_status
            self._health_expires_at = self._now() + timedelta(seconds=cache_ttl)
        log_timing(
            logger,
            self._settings,
            "llm.health",
            timer.elapsed_ms,
            available=health_status.available,
            warmed=health_status.warmed_up,
        )
        return health_status

    def _acquire_ollama_request(self, blocking: bool, purpose: str) -> bool:
        acquired = self._ollama_request_lock.acquire(blocking=blocking)
        if not acquired:
            logger.info(
                "Skipping LLM %s because another Ollama request is active",
                purpose,
            )
        return acquired

    def _release_ollama_request(self) -> None:
        self._ollama_request_lock.release()

    @property
    def _chat_url(self) -> str:
        return f"{self._settings.ollama_base_url.rstrip('/')}/api/chat"

    @property
    def _generate_url(self) -> str:
        return f"{self._settings.ollama_base_url.rstrip('/')}/api/generate"

    @property
    def _tags_url(self) -> str:
        return f"{self._settings.ollama_base_url.rstrip('/')}/api/tags"

    @property
    def _request_timeout_seconds(self) -> float:
        return min(
            self._settings.chat_timeout_seconds,
            self._settings.ollama_timeout_seconds,
        )

    @property
    def _warmup_timeout_seconds(self) -> float:
        return min(
            self._settings.ollama_warmup_timeout_seconds,
            self._settings.ollama_timeout_seconds,
        )

    @property
    def _parsed_keep_alive(self) -> str | int:
        """Parse keep_alive: convert pure numeric strings to int for Ollama."""
        raw = self._settings.ollama_keep_alive
        try:
            return int(raw)
        except (ValueError, TypeError):
            return raw

    @property
    def _is_gemma_model(self) -> bool:
        return self._settings.ollama_model.casefold().startswith("gemma")

    def _with_model_specific_options(
        self,
        payload: dict[str, Any],
        think: bool | None = None,
    ) -> dict[str, Any]:
        if self._is_gemma_model:
            payload["think"] = False if think is None else think
        return payload

    def _build_payload(
        self,
        message: str,
        stream: bool,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        think: bool | None = None,
    ) -> dict[str, Any]:
        return self._with_model_specific_options(
            {
                "model": self._settings.ollama_model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt or self._load_system_prompt(),
                    },
                    {"role": "user", "content": message},
                ],
                "stream": stream,
                "keep_alive": self._parsed_keep_alive,
                "options": {
                    "temperature": (
                        self._settings.llm_temperature
                        if temperature is None
                        else temperature
                    ),
                    "num_predict": (
                        self._settings.llm_max_tokens
                        if max_tokens is None
                        else max_tokens
                    ),
                    "num_ctx": self._settings.llm_num_ctx,
                },
            },
            think=think,
        )

    def _build_warmup_payload(self) -> dict[str, Any]:
        return self._with_model_specific_options(
            {
                "model": self._settings.ollama_model,
                "messages": [
                    {"role": "system", "content": self._load_general_chat_prompt()},
                    {"role": "user", "content": "พร้อมไหม"},
                ],
                "stream": False,
                "keep_alive": self._parsed_keep_alive,
                "options": {
                    "temperature": 0,
                    "num_predict": 8,
                    "num_ctx": self._settings.llm_num_ctx,
                },
            },
            think=False,
        )

    def _load_system_prompt(self) -> str:
        prompt_path = self._resolve_prompt_path(self._settings.system_prompt_path)
        try:
            prompt = prompt_path.read_text(encoding="utf-8").strip()
        except OSError:
            return DEFAULT_SYSTEM_PROMPT
        return prompt or DEFAULT_SYSTEM_PROMPT

    def _load_general_chat_prompt(self) -> str:
        return f"{self._load_system_prompt()}{GENERAL_CHAT_DEMO_RULES}"

    def _load_deep_think_general_prompt(self) -> str:
        return f"{self._load_system_prompt()}{DEEP_THINK_GENERAL_RULES}"

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

    @classmethod
    def is_thinking_request(cls, message: str) -> bool:
        normalized_message = cls._normalize_for_trigger(message)
        return any(
            cls._normalize_for_trigger(phrase) in normalized_message
            for phrase in THINKING_TRIGGER_PHRASES
        )

    @classmethod
    def strip_thinking_trigger(cls, message: str) -> str:
        cleaned_message = message
        for phrase in sorted(THINKING_TRIGGER_PHRASES, key=len, reverse=True):
            cleaned_message = re.sub(
                re.escape(phrase),
                " ",
                cleaned_message,
                flags=re.IGNORECASE,
            )
        cleaned_message = " ".join(cleaned_message.split())
        return cleaned_message or message

    @staticmethod
    def _normalize_for_trigger(text: str) -> str:
        return "".join(text.casefold().split())

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

    def _fallback(self, error: str, mark_unavailable: bool = True) -> LLMResponse:
        self._set_error(error, mark_unavailable=mark_unavailable)
        return LLMResponse(
            reply=self._fallback_reply_for_error(error),
            model=self._settings.ollama_model,
            source="fallback",
            fallback=True,
            error=error,
        )

    @staticmethod
    def _fallback_reply_for_error(error: str) -> str:
        normalized_error = error.casefold()
        if "timeout" in normalized_error:
            return (
                "ข้อนี้โมเดลหลักใช้เวลาคิดนานเกินไปนิดหนึ่ง "
                "ลองถามให้สั้นลงหรือกดถามซ้ำอีกครั้งได้ไหม"
            )
        if "model not found" in normalized_error:
            return "ยังไม่พบโมเดลที่ตั้งค่าไว้ใน Ollama ลองเช็กชื่อโมเดลก่อนนะ"
        if "connection" in normalized_error or "unavailable" in normalized_error:
            return "ตอนนี้ยังเชื่อมต่อโมเดลหลักไม่ได้ ลองเช็กว่า Ollama เปิดอยู่แล้วถามใหม่อีกครั้งนะ"
        return DEFAULT_FALLBACK_REPLY

    def _set_error(self, error: str, mark_unavailable: bool = True) -> None:
        self._last_error = error
        if not mark_unavailable:
            return
        with self._lock:
            if self._health_cache is not None:
                self._health_cache = LLMHealthStatus(
                    available=False,
                    model_present=self._health_cache.model_present,
                    warmed_up=self._health_cache.warmed_up,
                    source="live",
                    checked_at=self._now(),
                    last_error=error,
                    last_latency_ms=self._last_latency_ms,
                )
                self._health_expires_at = self._now() + timedelta(seconds=5)

    def _resume_keep_awake(self) -> None:
        """Unpause keep-awake loop when a real request comes in."""
        if self._keep_awake_paused:
            with self._lock:
                self._keep_awake_paused = False
            logger.info("Keep-awake auto-resumed due to incoming request")

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)


_llm_manager = LLMManager(settings=get_settings())


def get_llm_manager() -> LLMManager:
    return _llm_manager
