from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from threading import Lock
from uuid import uuid4

from server.config import Settings, get_settings, resolve_project_path
from server.utils.observability import log_timing, start_timer

logger = logging.getLogger(__name__)

try:
    import edge_tts
except ImportError:  # pragma: no cover - dependency validation happens at runtime
    edge_tts = None


@dataclass(frozen=True)
class TTSResult:
    ok: bool
    text: str
    audio_url: str | None = None
    provider: str | None = None
    error: str | None = None
    token: str | None = None


@dataclass(frozen=True)
class TTSStatus:
    tts_enabled: bool
    provider: str
    output_file: str
    current_token: str | None
    audio_ready: bool
    file_size_bytes: int
    last_generated_at: datetime | None
    last_error: str | None


class TTSService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._output_dir = resolve_project_path(settings.tts_output_dir)
        self._synthesis_lock = Lock()
        self._current_token: str | None = None
        self._pending_token: str | None = None
        self._last_generated_at: datetime | None = None
        self._last_error: str | None = None

    def synthesize(self, text: str, token: str | None = None) -> TTSResult:
        cleaned_text = text.strip()
        timer = start_timer()
        active_token = token or self._create_token()
        if not self._settings.tts_enabled:
            self._mark_failed_token(active_token, "tts disabled")
            return TTSResult(
                ok=False,
                text=cleaned_text,
                error="tts disabled",
                token=active_token,
            )
        if not cleaned_text:
            self._mark_failed_token(active_token, "empty text")
            return TTSResult(
                ok=False,
                text=cleaned_text,
                error="empty text",
                token=active_token,
            )

        provider = self._settings.tts_provider.strip().lower()
        if provider != "edge_tts":
            self._mark_failed_token(active_token, f"unsupported tts provider: {provider}")
            return TTSResult(
                ok=False,
                text=cleaned_text,
                error=f"unsupported tts provider: {provider}",
                token=active_token,
            )
        if edge_tts is None:
            self._mark_failed_token(active_token, "edge-tts is not installed")
            return TTSResult(
                ok=False,
                text=cleaned_text,
                error="edge-tts is not installed",
                token=active_token,
            )

        output_path = self.get_output_path(cleaned_text)
        try:
            with self._synthesis_lock:
                self._output_dir.mkdir(parents=True, exist_ok=True)
                output_path = self._write_audio_file(cleaned_text, output_path)
                self._current_token = active_token
                self._pending_token = active_token
                self._last_generated_at = self._now()
                self._last_error = None
                if self._settings.tts_overwrite_output:
                    self._cleanup_demo_mode_files(output_path)
                else:
                    self._cleanup_old_files()
        except Exception as exc:  # pragma: no cover - runtime/network dependent
            logger.warning("TTS generation failed: %s", exc.__class__.__name__)
            self._mark_failed_token(active_token, str(exc))
            return TTSResult(
                ok=False,
                text=cleaned_text,
                provider=provider,
                error=str(exc),
                token=active_token,
            )

        log_timing(
            logger,
            self._settings,
            "tts.generate",
            timer.elapsed_ms,
            provider=provider,
        )
        return TTSResult(
            ok=True,
            text=cleaned_text,
            audio_url=self.get_audio_url(cleaned_text, token=active_token),
            provider=provider,
            token=active_token,
        )

    def get_output_path(self, text: str = "") -> Path:
        return self._output_dir / self._build_filename(text.strip())

    def get_audio_url(self, text: str = "", token: str | None = None) -> str:
        if self._settings.tts_overwrite_output:
            active_token = token or self._current_token
            if active_token:
                return f"/voice/audio/current?token={active_token}"
            return "/voice/audio/current"
        return f"/static/{self._build_filename(text.strip())}"

    def create_pending_audio_url(self) -> tuple[str, str]:
        token = self._create_token()
        self._pending_token = token
        return token, self.get_audio_url(token=token)

    def get_current_audio_bytes(self, token: str | None = None) -> bytes | None:
        if token and token != self._current_token:
            return None
        output_path = self.get_output_path()
        try:
            audio_bytes = output_path.read_bytes()
        except OSError:
            return None
        if not audio_bytes:
            return None
        return audio_bytes

    def get_status(self) -> TTSStatus:
        visible_token = self._pending_token or self._current_token
        audio_bytes = self.get_current_audio_bytes(token=visible_token)
        return TTSStatus(
            tts_enabled=self._settings.tts_enabled,
            provider=self._settings.tts_provider,
            output_file=self._build_filename(""),
            current_token=visible_token,
            audio_ready=audio_bytes is not None,
            file_size_bytes=len(audio_bytes) if audio_bytes is not None else 0,
            last_generated_at=self._last_generated_at,
            last_error=self._last_error,
        )

    def _write_audio_file(self, text: str, output_path: Path) -> Path:
        if not self._settings.tts_overwrite_output:
            asyncio.run(self._synthesize_with_edge_tts(text, output_path))
            self._ensure_non_empty_file(output_path)
            return output_path

        temp_path = output_path.with_name(f".{output_path.stem}.{uuid4().hex}.tmp.mp3")
        try:
            asyncio.run(self._synthesize_with_edge_tts(text, temp_path))
            self._ensure_non_empty_file(temp_path)
            temp_path.replace(output_path)
            self._ensure_non_empty_file(output_path)
            return output_path
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    logger.warning("Failed to remove temp audio file: %s", temp_path.name)

    async def _synthesize_with_edge_tts(self, text: str, output_path: Path) -> None:
        communicator = edge_tts.Communicate(
            text=text,
            voice=self._settings.tts_default_voice,
        )
        await communicator.save(str(output_path))

    def _build_filename(self, text: str) -> str:
        if self._settings.tts_overwrite_output:
            return self._sanitize_filename(self._settings.tts_output_file)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
        return f"reply_{digest}.mp3"

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        cleaned_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename.strip())
        if not cleaned_name:
            return "current_reply.mp3"
        if not cleaned_name.lower().endswith(".mp3"):
            return f"{cleaned_name}.mp3"
        return cleaned_name

    def _cleanup_old_files(self, keep_count: int = 20) -> None:
        generated_files = sorted(
            self._output_dir.glob("reply_*.mp3"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for stale_file in generated_files[keep_count:]:
            try:
                stale_file.unlink()
            except OSError:
                logger.warning("Failed to remove stale audio file: %s", stale_file.name)

    def _cleanup_demo_mode_files(self, keep_path: Path) -> None:
        for stale_file in self._output_dir.iterdir():
            if stale_file == keep_path:
                continue
            if not (
                stale_file.name.startswith("reply_") and stale_file.suffix.lower() == ".mp3"
            ) and ".tmp.mp3" not in stale_file.name:
                continue
            try:
                stale_file.unlink()
            except OSError:
                logger.warning("Failed to remove stale demo audio file: %s", stale_file.name)

    @staticmethod
    def _ensure_non_empty_file(path: Path) -> None:
        try:
            file_size = path.stat().st_size
        except OSError as exc:
            raise ValueError("generated audio file is missing") from exc
        if file_size <= 0:
            raise ValueError("generated audio file is empty")

    @staticmethod
    def _create_token() -> str:
        return uuid4().hex

    def _mark_failed_token(self, token: str, error: str) -> None:
        self._last_error = error
        if self._pending_token == token:
            self._pending_token = self._current_token

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)


_tts_service = TTSService(get_settings())


def get_tts_service() -> TTSService:
    return _tts_service
