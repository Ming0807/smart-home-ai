from __future__ import annotations

import asyncio
import hashlib
import io
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import time
from threading import Lock, Thread
from uuid import uuid4
import wave

from server.config import Settings, get_settings, resolve_project_path
from server.utils.observability import log_timing, start_timer

logger = logging.getLogger(__name__)

EDGE_TTS_MAX_ATTEMPTS = 3
EDGE_TTS_RETRY_DELAY_SECONDS = 0.45

try:
    import edge_tts
except ImportError:  # pragma: no cover - dependency validation happens at runtime
    edge_tts = None

try:
    import av
except ImportError:  # pragma: no cover - optional voice-node conversion dependency
    av = None

try:
    import numpy as np
except ImportError:  # pragma: no cover - optional PyAV ndarray helper
    np = None


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
        self._state_lock = Lock()
        self._current_token: str | None = None
        self._pending_token: str | None = None
        self._wav_cache_token: str | None = None
        self._wav_cache_sample_rate: int | None = None
        self._wav_cache_bytes: bytes | None = None
        self._last_generated_at: datetime | None = None
        self._last_error: str | None = None

    def synthesize(self, text: str, token: str | None = None) -> TTSResult:
        cleaned_text = text.strip()
        timer = start_timer()
        active_token = token or self._create_token()
        if token is None:
            self._set_pending_token(active_token)
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
                if self._settings.tts_overwrite_output and not self._is_pending_token(active_token):
                    return TTSResult(
                        ok=False,
                        text=cleaned_text,
                        provider=provider,
                        error="audio superseded",
                        token=active_token,
                    )
                self._output_dir.mkdir(parents=True, exist_ok=True)
                output_path = self._write_audio_file_with_retries(
                    cleaned_text,
                    output_path,
                    active_token,
                )
                with self._state_lock:
                    if (
                        self._settings.tts_overwrite_output
                        and self._pending_token != active_token
                    ):
                        return TTSResult(
                            ok=False,
                            text=cleaned_text,
                            provider=provider,
                            error="audio superseded",
                            token=active_token,
                        )
                    self._current_token = active_token
                    self._pending_token = active_token
                    self._wav_cache_token = None
                    self._wav_cache_sample_rate = None
                    self._wav_cache_bytes = None
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
            active_token = token or self._get_current_token()
            if active_token:
                return f"/voice/audio/current?token={active_token}"
            return "/voice/audio/current"
        return f"/static/{self._build_filename(text.strip())}"

    def create_pending_audio_url(self) -> tuple[str, str]:
        token = self._create_token()
        self._set_pending_token(token)
        return token, self.get_audio_url(token=token)

    def get_current_audio_bytes(self, token: str | None = None) -> bytes | None:
        with self._state_lock:
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

    def get_current_audio_wav_bytes(
        self,
        token: str | None = None,
        sample_rate: int = 16000,
    ) -> bytes | None:
        with self._state_lock:
            active_token = token or self._current_token
            if token and token != self._current_token:
                return None
            if (
                active_token
                and active_token == self._wav_cache_token
                and sample_rate == self._wav_cache_sample_rate
                and self._wav_cache_bytes
            ):
                return self._wav_cache_bytes

        audio_bytes = self.get_current_audio_bytes(token=token)
        if audio_bytes is None or av is None:
            return None

        try:
            input_buffer = io.BytesIO(audio_bytes)
            output_buffer = io.BytesIO()
            resampler = av.audio.resampler.AudioResampler(
                format="s16",
                layout="mono",
                rate=sample_rate,
            )
            pcm_buffer = bytearray()

            with av.open(input_buffer, mode="r") as container:
                for frame in container.decode(audio=0):
                    resampled_frames = resampler.resample(frame)
                    if not isinstance(resampled_frames, list):
                        resampled_frames = [resampled_frames]
                    for resampled_frame in resampled_frames:
                        pcm_buffer.extend(self._audio_frame_to_pcm_bytes(resampled_frame))

            pcm_bytes = self._postprocess_voice_node_pcm_bytes(bytes(pcm_buffer))
            with wave.open(output_buffer, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm_bytes)

            wav_bytes = output_buffer.getvalue()
        except Exception as exc:  # pragma: no cover - codec/runtime dependent
            logger.warning("TTS MP3 to WAV conversion failed: %s", exc)
            return None

        if wav_bytes:
            with self._state_lock:
                if active_token == self._current_token:
                    self._wav_cache_token = active_token
                    self._wav_cache_sample_rate = sample_rate
                    self._wav_cache_bytes = wav_bytes
        return wav_bytes or None

    def get_status(self) -> TTSStatus:
        with self._state_lock:
            visible_token = self._pending_token or self._current_token
            last_generated_at = self._last_generated_at
            last_error = self._last_error
        audio_bytes = self.get_current_audio_bytes(token=visible_token)
        return TTSStatus(
            tts_enabled=self._settings.tts_enabled,
            provider=self._settings.tts_provider,
            output_file=self._build_filename(""),
            current_token=visible_token,
            audio_ready=audio_bytes is not None,
            file_size_bytes=len(audio_bytes) if audio_bytes is not None else 0,
            last_generated_at=last_generated_at,
            last_error=last_error,
        )

    def _write_audio_file(self, text: str, output_path: Path, token: str) -> Path:
        if not self._settings.tts_overwrite_output:
            self._run_coro_blocking(self._synthesize_with_edge_tts(text, output_path))
            self._ensure_non_empty_file(output_path)
            return output_path

        temp_path = output_path.with_name(f".{output_path.stem}.{uuid4().hex}.tmp.mp3")
        try:
            self._run_coro_blocking(self._synthesize_with_edge_tts(text, temp_path))
            self._ensure_non_empty_file(temp_path)
            if not self._is_pending_token(token):
                return output_path
            temp_path.replace(output_path)
            self._ensure_non_empty_file(output_path)
            return output_path
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    logger.warning("Failed to remove temp audio file: %s", temp_path.name)

    def _write_audio_file_with_retries(
        self,
        text: str,
        output_path: Path,
        token: str,
    ) -> Path:
        last_error: Exception | None = None
        for attempt in range(1, EDGE_TTS_MAX_ATTEMPTS + 1):
            try:
                return self._write_audio_file(text, output_path, token)
            except Exception as exc:
                last_error = exc
                if attempt >= EDGE_TTS_MAX_ATTEMPTS:
                    break
                if self._settings.tts_overwrite_output and not self._is_pending_token(token):
                    break
                logger.info(
                    "Retrying TTS generation after %s (%s/%s)",
                    exc.__class__.__name__,
                    attempt + 1,
                    EDGE_TTS_MAX_ATTEMPTS,
                )
                time.sleep(EDGE_TTS_RETRY_DELAY_SECONDS)

        if last_error is not None:
            raise last_error
        raise RuntimeError("tts retry failed without an exception")

    async def _synthesize_with_edge_tts(self, text: str, output_path: Path) -> None:
        communicator = edge_tts.Communicate(
            text=text,
            voice=self._settings.tts_default_voice,
        )
        await communicator.save(str(output_path))

    @staticmethod
    def _audio_frame_to_pcm_bytes(frame: object) -> bytes:
        if np is not None and hasattr(frame, "to_ndarray"):
            samples = frame.to_ndarray()
            samples = samples.reshape(-1).astype("<i2", copy=False)
            return samples.tobytes()

        chunks: list[bytes] = []
        for plane in frame.planes:  # type: ignore[attr-defined]
            chunks.append(bytes(plane))
        return b"".join(chunks)

    def _postprocess_voice_node_pcm_bytes(self, pcm_bytes: bytes) -> bytes:
        if np is None or not pcm_bytes:
            return pcm_bytes

        samples = np.frombuffer(pcm_bytes, dtype="<i2").astype(np.float32)
        if samples.size == 0:
            return pcm_bytes

        samples -= float(np.mean(samples))
        peak = float(np.max(np.abs(samples)))
        if peak <= 0:
            return pcm_bytes

        target_peak = max(
            0.10,
            min(0.98, self._settings.voice_node_wav_target_peak),
        ) * 32767.0
        max_gain = max(1.0, self._settings.voice_node_wav_max_gain)
        if peak < target_peak:
            gain = min(max_gain, target_peak / peak)
        else:
            gain = target_peak / peak

        processed = np.clip(samples * gain, -32768, 32767).astype("<i2")
        return processed.tobytes()

    @staticmethod
    def _run_coro_blocking(coro: object) -> None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(coro)  # type: ignore[arg-type]
            return

        result: dict[str, BaseException | None] = {"error": None}

        def runner() -> None:
            try:
                asyncio.run(coro)  # type: ignore[arg-type]
            except BaseException as exc:  # pragma: no cover - thread bridge
                result["error"] = exc

        thread = Thread(target=runner, name="tts-async-bridge", daemon=True)
        thread.start()
        thread.join()
        if result["error"] is not None:
            raise result["error"]

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

    def _set_pending_token(self, token: str) -> None:
        with self._state_lock:
            self._pending_token = token

    def _get_current_token(self) -> str | None:
        with self._state_lock:
            return self._current_token

    def _is_pending_token(self, token: str) -> bool:
        with self._state_lock:
            return self._pending_token == token

    def _mark_failed_token(self, token: str, error: str) -> None:
        with self._state_lock:
            self._last_error = error
            if self._pending_token == token:
                self._pending_token = self._current_token

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)


_tts_service = TTSService(get_settings())


def get_tts_service() -> TTSService:
    return _tts_service
