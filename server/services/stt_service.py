from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
import logging
from pathlib import Path
import tempfile
from threading import Lock

from fastapi import UploadFile

from server.config import Settings, get_settings
from server.utils.observability import log_timing, start_timer

logger = logging.getLogger(__name__)

try:
    from faster_whisper import WhisperModel
except ImportError:  # pragma: no cover - optional dependency at runtime
    WhisperModel = None


@dataclass(frozen=True)
class STTResult:
    ok: bool
    text: str
    provider: str
    error: str | None = None


class STTService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model_lock = Lock()
        self._whisper_model: WhisperModel | None = None
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="stt")
        self._warmed_up = False
        self._last_error: str | None = None

    async def transcribe_upload(self, audio_file: UploadFile) -> STTResult:
        provider = self._settings.stt_provider.strip().lower()
        temp_path: Path | None = None

        try:
            audio_bytes = await audio_file.read()
            if not audio_bytes:
                return STTResult(
                    ok=False,
                    text="",
                    provider=provider,
                    error="audio file is empty",
                )

            temp_path = self._write_temp_audio_file(
                filename=audio_file.filename,
                content_type=audio_file.content_type,
                audio_bytes=audio_bytes,
            )

            if provider == "faster_whisper":
                return self._transcribe_with_timeout(temp_path)

            return STTResult(
                ok=False,
                text="",
                provider=provider,
                error=f"unsupported stt provider: {provider}",
            )
        except Exception as exc:  # pragma: no cover - runtime dependency/environment
            logger.warning("STT processing failed: %s", exc)
            return STTResult(
                ok=False,
                text="",
                provider=provider,
                error=str(exc),
            )
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    logger.warning("Failed to remove temporary STT file: %s", temp_path)

    def _transcribe_with_timeout(self, audio_path: Path) -> STTResult:
        timer = start_timer()
        future = self._executor.submit(self._run_faster_whisper, audio_path)
        timeout_seconds = self._settings.stt_timeout_seconds
        if not self._warmed_up:
            timeout_seconds = max(timeout_seconds, 120.0)

        try:
            result = future.result(timeout=timeout_seconds)
        except FutureTimeoutError:
            future.cancel()
            self._last_error = "stt timed out"
            logger.warning("STT timed out after %.1f seconds", timeout_seconds)
            return STTResult(
                ok=False,
                text="",
                provider="faster_whisper",
                error="stt timed out",
            )

        if result.ok:
            self._last_error = None
        else:
            self._last_error = result.error
            logger.warning("STT failed: %s", result.error)

        log_timing(
            logger,
            self._settings,
            "stt.transcribe",
            timer.elapsed_ms,
            provider="faster_whisper",
            status="ok" if result.ok else "error",
        )
        return result

    def _run_faster_whisper(self, audio_path: Path) -> STTResult:
        if WhisperModel is None:
            return STTResult(
                ok=False,
                text="",
                provider="faster_whisper",
                error="faster-whisper is not installed",
            )

        model = self._get_whisper_model()
        segments, _ = model.transcribe(
            str(audio_path),
            language=self._settings.stt_language or None,
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
        if not transcript:
            return STTResult(
                ok=False,
                text="",
                provider="faster_whisper",
                error="no speech detected",
            )

        return STTResult(
            ok=True,
            text=transcript,
            provider="faster_whisper",
        )

    def _get_whisper_model(self) -> WhisperModel:
        with self._model_lock:
            if self._whisper_model is None:
                self._whisper_model = WhisperModel(
                    self._settings.stt_model,
                    device="cpu",
                    compute_type="int8",
                )
            self._warmed_up = True
            return self._whisper_model

    def warmup(self) -> None:
        provider = self._settings.stt_provider.strip().lower()
        if provider != "faster_whisper":
            return

        timer = start_timer()
        try:
            self._get_whisper_model()
            self._last_error = None
            log_timing(
                logger,
                self._settings,
                "stt.warmup",
                timer.elapsed_ms,
                provider=provider,
                status="ok",
            )
        except Exception as exc:  # pragma: no cover - runtime dependency/environment
            self._last_error = str(exc)
            logger.warning("STT warmup failed: %s", exc)
            log_timing(
                logger,
                self._settings,
                "stt.warmup",
                timer.elapsed_ms,
                provider=provider,
                status="error",
            )

    @staticmethod
    def _write_temp_audio_file(
        filename: str | None,
        content_type: str | None,
        audio_bytes: bytes,
    ) -> Path:
        suffix = STTService._resolve_suffix(filename=filename, content_type=content_type)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(audio_bytes)
            return Path(temp_file.name)

    @staticmethod
    def _resolve_suffix(filename: str | None, content_type: str | None) -> str:
        if filename and "." in filename:
            return "." + filename.rsplit(".", 1)[-1].lower()

        content_type_map = {
            "audio/webm": ".webm",
            "audio/wav": ".wav",
            "audio/x-wav": ".wav",
            "audio/mpeg": ".mp3",
            "audio/mp3": ".mp3",
            "audio/ogg": ".ogg",
            "audio/mp4": ".mp4",
            "audio/x-m4a": ".m4a",
        }
        return content_type_map.get((content_type or "").lower(), ".webm")


_stt_service = STTService(get_settings())


def get_stt_service() -> STTService:
    return _stt_service
