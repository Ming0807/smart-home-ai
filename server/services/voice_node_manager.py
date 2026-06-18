from __future__ import annotations

from array import array
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from difflib import SequenceMatcher
import io
from threading import Lock
from uuid import uuid4
import wave

from server.config import Settings, get_settings
from server.models.voice_node import (
    AssistantAudioData,
    VoiceNodeAudioHistoryClearResponse,
    VoiceNodeAudioHistoryItem,
    VoiceNodeAudioHistoryResponse,
    VoiceNodeAudioReportResponse,
    VoiceNodeAudioStatusResponse,
    VoiceNodeCommandData,
    VoiceNodeCommandPollResponse,
    VoiceNodeCommandQueueResponse,
    VoiceNodeCommandType,
    VoiceNodeConfigResponse,
    VoiceNodeConfigUpdateRequest,
    VoiceNodeHeartbeatRequest,
    VoiceNodePlaybackStatusRequest,
    VoiceNodeStatusResponse,
    VoiceNodeStreamStatusResponse,
)
from server.services.sqlite_log_store import SQLiteLogStore, get_sqlite_log_store


@dataclass(frozen=True)
class VoiceNodeRecord:
    device_id: str
    firmware_version: str | None
    state: str
    ip_address: str | None
    last_seen_at: datetime


@dataclass(frozen=True)
class VoiceNodeAudioRecord:
    device_id: str
    received_at: datetime
    server_received_at: datetime
    stt_ok: bool
    stt_error: str | None
    stt_raw_text: str | None
    expected_text: str | None
    stt_similarity: float | None
    data: AssistantAudioData
    uploaded_audio_bytes: bytes
    uploaded_audio_content_type: str
    audio_metrics: VoiceNodeAudioMetrics
    playback_record: VoiceNodePlaybackRecord | None = None


@dataclass(frozen=True)
class VoiceNodeAudioMetrics:
    duration_ms: int | None = None
    sample_rate_hz: int | None = None
    channel_count: int | None = None
    bits_per_sample: int | None = None
    peak_ratio: float | None = None
    rms_ratio: float | None = None
    clipping_ratio: float | None = None
    silence_ratio: float | None = None
    quality: str = "unknown"
    quality_notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class VoiceNodePlaybackRecord:
    device_id: str
    reported_at: datetime
    stage: str
    ok: bool
    error: str | None
    audio_url: str | None
    audio_size_bytes: int | None


@dataclass(frozen=True)
class VoiceNodeStreamRecord:
    device_id: str
    connected: bool
    connected_at: datetime | None
    disconnected_at: datetime | None
    last_frame_at: datetime | None
    frame_count: int
    total_bytes: int
    sample_rate_hz: int
    channels: int
    bits_per_sample: int
    last_peak_ratio: float | None = None
    last_rms_ratio: float | None = None
    vad_rms_threshold: float = 0.025
    vad_start_frames: int = 3
    vad_end_frames: int = 10
    speech_candidate_frames: int = 0
    silence_frame_count: int = 0
    speech_active: bool = False
    speech_frame_count: int = 0
    speech_bytes: int = 0
    utterance_count: int = 0
    last_speech_at: datetime | None = None
    last_error: str | None = None


@dataclass(frozen=True)
class VoiceNodeCommandRecord:
    command_id: str
    device_id: str
    type: VoiceNodeCommandType
    created_at: datetime
    audio_url: str | None = None
    expected_text: str | None = None


@dataclass(frozen=True)
class VoiceNodeRuntimeConfig:
    enabled: bool | None = None
    record_seconds: int | None = None
    mic_record_gain: int | None = None
    vad_enabled: bool | None = None
    vad_threshold: int | None = None
    vad_min_record_ms: int | None = None
    vad_silence_stop_ms: int | None = None


class VoiceNodeManager:
    """In-memory status/config source for the ESP32-S3 voice node."""

    def __init__(
        self,
        settings: Settings,
        log_store: SQLiteLogStore | None = None,
    ) -> None:
        self._settings = settings
        self._log_store = log_store or get_sqlite_log_store()
        self._lock = Lock()
        self._nodes: dict[str, VoiceNodeRecord] = {}
        self._latest_audio: dict[str, VoiceNodeAudioRecord] = {}
        self._audio_history: dict[str, list[VoiceNodeAudioRecord]] = {}
        self._latest_playback: dict[str, VoiceNodePlaybackRecord] = {}
        self._commands: dict[str, list[VoiceNodeCommandRecord]] = {}
        self._active_expected_text: dict[str, str] = {}
        self._runtime_config: dict[str, VoiceNodeRuntimeConfig] = {}
        self._conversation_mode_enabled: dict[str, bool] = {}
        self._conversation_mode_started_at: dict[str, datetime] = {}
        self._wake_mode_enabled: dict[str, bool] = {}
        self._wake_conversation_active: dict[str, bool] = {}
        self._auto_wake_suspended: dict[str, bool] = {}
        self._last_auto_wake_at: dict[str, datetime] = {}
        self._pending_conversation_timeout_notice: dict[str, datetime] = {}
        self._stream_status: dict[str, VoiceNodeStreamRecord] = {}

    def record_heartbeat(
        self,
        request: VoiceNodeHeartbeatRequest,
    ) -> datetime:
        now = datetime.now(timezone.utc)
        with self._lock:
            previous_record = self._nodes.get(request.device_id)
            state_changed = (
                previous_record is None
                or previous_record.state != request.state
            )
            self._nodes[request.device_id] = VoiceNodeRecord(
                device_id=request.device_id,
                firmware_version=request.firmware_version,
                state=request.state,
                ip_address=request.ip_address,
                last_seen_at=now,
            )
            timed_out = self._reconcile_stale_modes_unlocked(
                request.device_id,
                request.state,
                now,
            )
            if not timed_out:
                self._ensure_auto_wake_unlocked(request.device_id)
        self._log_store.record_voice_node_heartbeat(
            device_id=request.device_id,
            state=request.state,
            firmware_version=request.firmware_version,
            ip_address=request.ip_address,
            seen_at=now,
            state_changed=state_changed,
        )
        return now

    def record_audio_result(
        self,
        device_id: str,
        stt_ok: bool,
        stt_error: str | None,
        stt_raw_text: str | None,
        data: AssistantAudioData,
        uploaded_audio_bytes: bytes,
        uploaded_audio_content_type: str | None,
        server_received_at: datetime | None = None,
    ) -> datetime:
        resolved_device_id = self._resolve_device_id(device_id)
        now = datetime.now(timezone.utc)
        resolved_server_received_at = server_received_at or now
        should_auto_wake = False
        with self._lock:
            expected_text = self._active_expected_text.pop(resolved_device_id, None)
            if self._conversation_mode_enabled.get(resolved_device_id) and not data.keep_mic_open:
                self._conversation_mode_enabled[resolved_device_id] = False
                self._conversation_mode_started_at.pop(resolved_device_id, None)
                should_auto_wake = True
        similarity = self._calculate_similarity(expected_text, data.heard_text)
        audio_metrics = self._analyze_wav_audio(uploaded_audio_bytes)
        record = VoiceNodeAudioRecord(
            device_id=resolved_device_id,
            received_at=now,
            server_received_at=resolved_server_received_at,
            stt_ok=stt_ok,
            stt_error=stt_error,
            stt_raw_text=stt_raw_text,
            expected_text=expected_text,
            stt_similarity=similarity,
            data=data,
            uploaded_audio_bytes=uploaded_audio_bytes,
            uploaded_audio_content_type=uploaded_audio_content_type or "audio/wav",
            audio_metrics=audio_metrics,
        )
        with self._lock:
            self._latest_audio[resolved_device_id] = record
            history = self._audio_history.setdefault(resolved_device_id, [])
            history.insert(0, record)
            del history[10:]
            if should_auto_wake:
                self._ensure_auto_wake_unlocked(resolved_device_id)
        self._log_store.record_voice_node_audio_result(
            device_id=resolved_device_id,
            received_at=now,
            stt_ok=stt_ok,
            stt_error=stt_error,
            stt_raw_text=stt_raw_text,
            expected_text=expected_text,
            stt_similarity=similarity,
            heard_text=data.heard_text,
            reply=data.reply,
            intent=str(data.intent),
            source=str(data.source),
            action=str(data.action),
            keep_mic_open=data.keep_mic_open,
            uploaded_audio_size_bytes=len(uploaded_audio_bytes),
            uploaded_audio_duration_ms=audio_metrics.duration_ms,
            uploaded_audio_quality=audio_metrics.quality,
            uploaded_audio_peak_ratio=audio_metrics.peak_ratio,
            uploaded_audio_rms_ratio=audio_metrics.rms_ratio,
        )
        return now

    def record_playback_status(self, request: VoiceNodePlaybackStatusRequest) -> datetime:
        resolved_device_id = self._resolve_device_id(request.device_id)
        now = datetime.now(timezone.utc)
        playback_record = VoiceNodePlaybackRecord(
            device_id=resolved_device_id,
            reported_at=now,
            stage=request.stage,
            ok=request.ok,
            error=request.error,
            audio_url=request.audio_url,
            audio_size_bytes=request.audio_size_bytes,
        )
        with self._lock:
            self._latest_playback[resolved_device_id] = playback_record
            latest_audio = self._latest_audio.get(resolved_device_id)
            if latest_audio is not None:
                updated_audio = replace(latest_audio, playback_record=playback_record)
                self._latest_audio[resolved_device_id] = updated_audio
                history = self._audio_history.get(resolved_device_id, [])
                if history and history[0].received_at == latest_audio.received_at:
                    history[0] = updated_audio
        self._log_store.record_voice_node_playback_status(
            device_id=resolved_device_id,
            reported_at=now,
            stage=request.stage,
            ok=request.ok,
            error=request.error,
            audio_url=request.audio_url,
            audio_size_bytes=request.audio_size_bytes,
        )
        return now

    def record_stream_open(
        self,
        device_id: str | None,
        sample_rate_hz: int = 16000,
        channels: int = 1,
        bits_per_sample: int = 16,
    ) -> datetime:
        resolved_device_id = self._resolve_device_id(device_id)
        now = datetime.now(timezone.utc)
        with self._lock:
            self._stream_status[resolved_device_id] = VoiceNodeStreamRecord(
                device_id=resolved_device_id,
                connected=True,
                connected_at=now,
                disconnected_at=None,
                last_frame_at=None,
                frame_count=0,
                total_bytes=0,
                sample_rate_hz=sample_rate_hz,
                channels=channels,
                bits_per_sample=bits_per_sample,
                vad_rms_threshold=self._settings.voice_node_stream_vad_rms_threshold,
                vad_start_frames=self._settings.voice_node_stream_vad_start_frames,
                vad_end_frames=self._settings.voice_node_stream_vad_end_frames,
            )
        return now

    def record_stream_chunk(
        self,
        device_id: str | None,
        chunk: bytes,
        sample_rate_hz: int = 16000,
        channels: int = 1,
        bits_per_sample: int = 16,
    ) -> datetime:
        resolved_device_id = self._resolve_device_id(device_id)
        now = datetime.now(timezone.utc)
        peak_ratio, rms_ratio = self._analyze_pcm16_chunk(chunk)
        vad_threshold = self._settings.voice_node_stream_vad_rms_threshold
        vad_start_frames = max(1, self._settings.voice_node_stream_vad_start_frames)
        vad_end_frames = max(1, self._settings.voice_node_stream_vad_end_frames)
        is_speech_frame = rms_ratio is not None and rms_ratio >= vad_threshold
        with self._lock:
            current = self._stream_status.get(resolved_device_id)
            if current is None:
                current = VoiceNodeStreamRecord(
                    device_id=resolved_device_id,
                    connected=True,
                    connected_at=now,
                    disconnected_at=None,
                    last_frame_at=None,
                    frame_count=0,
                    total_bytes=0,
                    sample_rate_hz=sample_rate_hz,
                    channels=channels,
                    bits_per_sample=bits_per_sample,
                    vad_rms_threshold=vad_threshold,
                    vad_start_frames=vad_start_frames,
                    vad_end_frames=vad_end_frames,
                )
            utterance_count = current.utterance_count
            speech_candidate_frames = (
                current.speech_candidate_frames + 1 if is_speech_frame else 0
            )
            silence_frame_count = 0
            speech_active = current.speech_active
            just_started = False
            if not speech_active and speech_candidate_frames >= vad_start_frames:
                speech_active = True
                just_started = True
                utterance_count += 1
            if speech_active and not is_speech_frame:
                silence_frame_count = current.silence_frame_count + 1
                if silence_frame_count >= vad_end_frames:
                    speech_active = False
                    speech_candidate_frames = 0
            elif is_speech_frame:
                silence_frame_count = 0

            speech_frame_increment = 0
            speech_byte_increment = 0
            if just_started:
                speech_frame_increment = speech_candidate_frames
                speech_byte_increment = len(chunk) * speech_candidate_frames
            elif speech_active and is_speech_frame:
                speech_frame_increment = 1
                speech_byte_increment = len(chunk)
            self._stream_status[resolved_device_id] = replace(
                current,
                connected=True,
                last_frame_at=now,
                disconnected_at=None,
                frame_count=current.frame_count + 1,
                total_bytes=current.total_bytes + len(chunk),
                sample_rate_hz=sample_rate_hz,
                channels=channels,
                bits_per_sample=bits_per_sample,
                last_peak_ratio=peak_ratio,
                last_rms_ratio=rms_ratio,
                vad_rms_threshold=vad_threshold,
                vad_start_frames=vad_start_frames,
                vad_end_frames=vad_end_frames,
                speech_candidate_frames=speech_candidate_frames,
                silence_frame_count=silence_frame_count,
                speech_active=speech_active,
                speech_frame_count=current.speech_frame_count + speech_frame_increment,
                speech_bytes=current.speech_bytes + speech_byte_increment,
                utterance_count=utterance_count,
                last_speech_at=now if speech_frame_increment else current.last_speech_at,
                last_error=None,
            )
        return now

    def record_stream_close(
        self,
        device_id: str | None,
        error: str | None = None,
    ) -> datetime:
        resolved_device_id = self._resolve_device_id(device_id)
        now = datetime.now(timezone.utc)
        with self._lock:
            current = self._stream_status.get(resolved_device_id)
            if current is None:
                current = VoiceNodeStreamRecord(
                    device_id=resolved_device_id,
                    connected=False,
                    connected_at=None,
                    disconnected_at=now,
                    last_frame_at=None,
                    frame_count=0,
                    total_bytes=0,
                    sample_rate_hz=self._settings.voice_node_sample_rate,
                    channels=1,
                    bits_per_sample=16,
                    vad_rms_threshold=self._settings.voice_node_stream_vad_rms_threshold,
                    vad_start_frames=self._settings.voice_node_stream_vad_start_frames,
                    vad_end_frames=self._settings.voice_node_stream_vad_end_frames,
                    last_error=error,
                )
            self._stream_status[resolved_device_id] = replace(
                current,
                connected=False,
                speech_active=False,
                silence_frame_count=0,
                disconnected_at=now,
                last_error=error,
            )
        return now

    def get_stream_status(self, device_id: str | None = None) -> VoiceNodeStreamStatusResponse:
        resolved_device_id = self._resolve_device_id(device_id)
        with self._lock:
            record = self._stream_status.get(resolved_device_id)

        if record is None:
            return VoiceNodeStreamStatusResponse(device_id=resolved_device_id)

        bytes_per_second = (
            record.sample_rate_hz
            * max(1, record.channels)
            * max(1, record.bits_per_sample // 8)
        )
        estimated_audio_seconds = (
            round(record.total_bytes / bytes_per_second, 2) if bytes_per_second > 0 else 0.0
        )
        speech_audio_seconds = (
            round(record.speech_bytes / bytes_per_second, 2) if bytes_per_second > 0 else 0.0
        )
        return VoiceNodeStreamStatusResponse(
            device_id=resolved_device_id,
            connected=record.connected,
            connected_at=record.connected_at,
            disconnected_at=record.disconnected_at,
            last_frame_at=record.last_frame_at,
            seconds_since_last_frame=(
                self._seconds_since(record.last_frame_at) if record.last_frame_at else None
            ),
            frame_count=record.frame_count,
            total_bytes=record.total_bytes,
            estimated_audio_seconds=estimated_audio_seconds,
            sample_rate_hz=record.sample_rate_hz,
            channels=record.channels,
            bits_per_sample=record.bits_per_sample,
            last_peak_ratio=record.last_peak_ratio,
            last_rms_ratio=record.last_rms_ratio,
            vad_rms_threshold=record.vad_rms_threshold,
            vad_start_frames=record.vad_start_frames,
            vad_end_frames=record.vad_end_frames,
            speech_candidate_frames=record.speech_candidate_frames,
            silence_frame_count=record.silence_frame_count,
            speech_active=record.speech_active,
            speech_frame_count=record.speech_frame_count,
            speech_audio_seconds=speech_audio_seconds,
            utterance_count=record.utterance_count,
            last_speech_at=record.last_speech_at,
            last_error=record.last_error,
        )

    def get_config(self, device_id: str | None = None) -> VoiceNodeConfigResponse:
        resolved_device_id = self._resolve_device_id(device_id)
        config = self._get_runtime_config(resolved_device_id)
        return VoiceNodeConfigResponse(
            device_id=resolved_device_id,
            enabled=self._value_or_default(config.enabled, self._settings.voice_node_enabled),
            wake_word=self._settings.voice_node_wake_word,
            record_seconds=self._value_or_default(
                config.record_seconds,
                self._settings.voice_node_record_seconds,
            ),
            sample_rate=self._settings.voice_node_sample_rate,
            reply_sample_rate=self._settings.voice_node_reply_sample_rate,
            audio_format=self._settings.voice_node_audio_format,
            reply_audio_format=self._settings.voice_node_reply_audio_format,
            mic_record_gain=self._value_or_default(
                config.mic_record_gain,
                self._settings.voice_node_mic_record_gain,
            ),
            vad_enabled=self._value_or_default(
                config.vad_enabled,
                self._settings.voice_node_vad_enabled,
            ),
            vad_threshold=self._value_or_default(
                config.vad_threshold,
                self._settings.voice_node_vad_threshold,
            ),
            vad_min_record_ms=self._value_or_default(
                config.vad_min_record_ms,
                self._settings.voice_node_vad_min_record_ms,
            ),
            vad_silence_stop_ms=self._value_or_default(
                config.vad_silence_stop_ms,
                self._settings.voice_node_vad_silence_stop_ms,
            ),
            heartbeat_endpoint="/voice-node/heartbeat",
            audio_endpoint="/assistant/audio",
            status_endpoint="/voice-node/status",
        )

    def update_config(
        self,
        request: VoiceNodeConfigUpdateRequest,
        device_id: str | None = None,
    ) -> VoiceNodeConfigResponse:
        resolved_device_id = self._resolve_device_id(device_id)
        with self._lock:
            current_config = self._runtime_config.get(resolved_device_id, VoiceNodeRuntimeConfig())
            updated_config = VoiceNodeRuntimeConfig(
                enabled=self._optional_update(request.enabled, current_config.enabled),
                record_seconds=self._optional_update(
                    request.record_seconds,
                    current_config.record_seconds,
                ),
                mic_record_gain=self._optional_update(
                    request.mic_record_gain,
                    current_config.mic_record_gain,
                ),
                vad_enabled=self._optional_update(request.vad_enabled, current_config.vad_enabled),
                vad_threshold=self._optional_update(
                    request.vad_threshold,
                    current_config.vad_threshold,
                ),
                vad_min_record_ms=self._optional_update(
                    request.vad_min_record_ms,
                    current_config.vad_min_record_ms,
                ),
                vad_silence_stop_ms=self._optional_update(
                    request.vad_silence_stop_ms,
                    current_config.vad_silence_stop_ms,
                ),
            )
            self._runtime_config[resolved_device_id] = updated_config
        return self.get_config(device_id=resolved_device_id)

    def get_status(self, device_id: str | None = None) -> VoiceNodeStatusResponse:
        resolved_device_id = self._resolve_device_id(device_id)
        with self._lock:
            self._drop_expired_commands_unlocked(resolved_device_id)
            record = self._nodes.get(resolved_device_id)
            pending_command_count = self._pending_command_count_unlocked(resolved_device_id)

        if record is None:
            return VoiceNodeStatusResponse(
                device_id=resolved_device_id,
                online=False,
                enabled=self._settings.voice_node_enabled,
                conversation_mode_enabled=self._conversation_mode_enabled.get(
                    resolved_device_id,
                    False,
                ),
                wake_mode_enabled=self._wake_mode_enabled.get(resolved_device_id, False),
                wake_conversation_active=self._wake_conversation_active.get(
                    resolved_device_id,
                    False,
                ),
                pending_command_count=pending_command_count,
            )

        seconds_since_heartbeat = self._seconds_since(record.last_seen_at)
        return VoiceNodeStatusResponse(
            device_id=resolved_device_id,
            online=seconds_since_heartbeat <= self._settings.voice_node_heartbeat_timeout_seconds,
            enabled=self._settings.voice_node_enabled,
            conversation_mode_enabled=self._conversation_mode_enabled.get(
                resolved_device_id,
                False,
            ),
            wake_mode_enabled=self._wake_mode_enabled.get(resolved_device_id, False),
            wake_conversation_active=self._wake_conversation_active.get(
                resolved_device_id,
                False,
            ),
            state=record.state,  # type: ignore[arg-type]
            firmware_version=record.firmware_version,
            ip_address=record.ip_address,
            last_seen_at=record.last_seen_at,
            seconds_since_heartbeat=seconds_since_heartbeat,
            pending_command_count=pending_command_count,
        )

    def queue_command(
        self,
        command_type: VoiceNodeCommandType,
        device_id: str | None = None,
        audio_url: str | None = None,
        expected_text: str | None = None,
    ) -> VoiceNodeCommandQueueResponse:
        resolved_device_id = self._resolve_device_id(device_id)
        record = VoiceNodeCommandRecord(
            command_id=uuid4().hex,
            device_id=resolved_device_id,
            type=command_type,
            created_at=datetime.now(timezone.utc),
            audio_url=audio_url,
            expected_text=(expected_text or "").strip() or None,
        )
        with self._lock:
            self._drop_expired_commands_unlocked(resolved_device_id)
            if command_type == "conversation_start":
                self._auto_wake_suspended[resolved_device_id] = False
                self._conversation_mode_enabled[resolved_device_id] = True
                self._conversation_mode_started_at[resolved_device_id] = record.created_at
                self._wake_mode_enabled[resolved_device_id] = False
                self._wake_conversation_active[resolved_device_id] = False
            elif command_type == "conversation_stop":
                self._auto_wake_suspended[resolved_device_id] = True
                self._conversation_mode_enabled[resolved_device_id] = False
                self._conversation_mode_started_at.pop(resolved_device_id, None)
            elif command_type in {"wake_listen_start", "stream_test_start", "stream_process_start"}:
                self._conversation_mode_enabled[resolved_device_id] = False
                self._conversation_mode_started_at.pop(resolved_device_id, None)
                if command_type == "wake_listen_start":
                    self._last_auto_wake_at[resolved_device_id] = record.created_at
            queue = self._commands.setdefault(resolved_device_id, [])
            queue.append(record)
            pending_count = len(queue)
        self._log_store.record_voice_node_command(
            device_id=resolved_device_id,
            command_id=record.command_id,
            command_type=record.type,
            queued_at=record.created_at,
            audio_url=record.audio_url,
            expected_text=record.expected_text,
            pending_command_count=pending_count,
        )

        return VoiceNodeCommandQueueResponse(
            device_id=resolved_device_id,
            command=self._to_command_data(record),
            pending_command_count=pending_count,
        )

    def queue_wake_listen_start(
        self,
        device_id: str | None = None,
    ) -> VoiceNodeCommandQueueResponse:
        resolved_device_id = self._resolve_device_id(device_id)
        with self._lock:
            self._auto_wake_suspended[resolved_device_id] = False
            self._conversation_mode_enabled[resolved_device_id] = False
            self._wake_mode_enabled[resolved_device_id] = True
            self._wake_conversation_active[resolved_device_id] = False
        return self.queue_command("wake_listen_start", device_id=resolved_device_id)

    def queue_wake_listen_stop(
        self,
        device_id: str | None = None,
    ) -> VoiceNodeCommandQueueResponse:
        resolved_device_id = self._resolve_device_id(device_id)
        with self._lock:
            self._auto_wake_suspended[resolved_device_id] = True
            self._wake_mode_enabled[resolved_device_id] = False
            self._wake_conversation_active[resolved_device_id] = False
            self._last_auto_wake_at.pop(resolved_device_id, None)
        return self.queue_command("wake_listen_stop", device_id=resolved_device_id)

    def pop_conversation_timeout_notice(self, device_id: str | None = None) -> bool:
        resolved_device_id = self._resolve_device_id(device_id)
        with self._lock:
            return (
                self._pending_conversation_timeout_notice.pop(resolved_device_id, None)
                is not None
            )

    def is_wake_conversation_active(self, device_id: str | None = None) -> bool:
        resolved_device_id = self._resolve_device_id(device_id)
        with self._lock:
            return self._wake_conversation_active.get(resolved_device_id, False)

    def set_wake_mode_enabled(
        self,
        device_id: str | None,
        enabled: bool,
    ) -> None:
        resolved_device_id = self._resolve_device_id(device_id)
        with self._lock:
            self._wake_mode_enabled[resolved_device_id] = enabled
            if not enabled:
                self._wake_conversation_active[resolved_device_id] = False
            else:
                self._conversation_mode_enabled[resolved_device_id] = False

    def set_wake_conversation_active(
        self,
        device_id: str | None,
        active: bool,
    ) -> None:
        resolved_device_id = self._resolve_device_id(device_id)
        with self._lock:
            self._wake_conversation_active[resolved_device_id] = active

    def pop_next_command(self, device_id: str | None = None) -> VoiceNodeCommandPollResponse:
        resolved_device_id = self._resolve_device_id(device_id)
        with self._lock:
            self._drop_expired_commands_unlocked(resolved_device_id)
            queue = self._commands.setdefault(resolved_device_id, [])
            record = queue.pop(0) if queue else None
            if record is not None and record.type == "record_once":
                if record.expected_text:
                    self._active_expected_text[resolved_device_id] = record.expected_text
                else:
                    self._active_expected_text.pop(resolved_device_id, None)

        return VoiceNodeCommandPollResponse(
            command=self._to_command_data(record) if record is not None else None,
        )

    def get_audio_status(self, device_id: str | None = None) -> VoiceNodeAudioStatusResponse:
        resolved_device_id = self._resolve_device_id(device_id)
        with self._lock:
            record = self._latest_audio.get(resolved_device_id)
            playback_record = self._latest_playback.get(resolved_device_id)

        if record is None:
            return VoiceNodeAudioStatusResponse(
                device_id=resolved_device_id,
                has_result=False,
                playback_reported_at=playback_record.reported_at if playback_record else None,
                playback_stage=playback_record.stage if playback_record else None,
                playback_ok=playback_record.ok if playback_record else None,
                playback_error=playback_record.error if playback_record else None,
                playback_audio_url=playback_record.audio_url if playback_record else None,
                playback_audio_size_bytes=(
                    playback_record.audio_size_bytes if playback_record else None
                ),
            )

        data = record.data
        resolved_playback_record = record.playback_record or playback_record
        metrics = record.audio_metrics
        return VoiceNodeAudioStatusResponse(
            device_id=resolved_device_id,
            has_result=True,
            received_at=record.received_at,
            server_received_at=record.server_received_at,
            server_processing_ms=self._duration_ms(record.server_received_at, record.received_at),
            playback_after_processing_ms=self._duration_ms(
                record.received_at,
                resolved_playback_record.reported_at if resolved_playback_record else None,
            ),
            seconds_since_received=self._seconds_since(record.received_at),
            stt_ok=record.stt_ok,
            stt_error=record.stt_error,
            stt_raw_text=record.stt_raw_text,
            expected_text=record.expected_text,
            stt_similarity=record.stt_similarity,
            heard_text=data.heard_text,
            reply=data.reply,
            intent=data.intent,
            source=data.source,
            action=data.action,
            keep_mic_open=data.keep_mic_open,
            reply_audio_url=data.reply_audio_url,
            reply_audio_format=data.reply_audio_format,
            uploaded_audio_url=f"/voice-node/audio/uploaded?device_id={resolved_device_id}",
            uploaded_audio_content_type=record.uploaded_audio_content_type,
            uploaded_audio_size_bytes=len(record.uploaded_audio_bytes),
            uploaded_audio_duration_ms=metrics.duration_ms,
            uploaded_audio_sample_rate_hz=metrics.sample_rate_hz,
            uploaded_audio_peak_ratio=metrics.peak_ratio,
            uploaded_audio_rms_ratio=metrics.rms_ratio,
            uploaded_audio_clipping_ratio=metrics.clipping_ratio,
            uploaded_audio_silence_ratio=metrics.silence_ratio,
            uploaded_audio_quality=metrics.quality,
            uploaded_audio_quality_notes=list(metrics.quality_notes),
            playback_reported_at=resolved_playback_record.reported_at if resolved_playback_record else None,
            playback_stage=resolved_playback_record.stage if resolved_playback_record else None,
            playback_ok=resolved_playback_record.ok if resolved_playback_record else None,
            playback_error=resolved_playback_record.error if resolved_playback_record else None,
            playback_audio_url=resolved_playback_record.audio_url if resolved_playback_record else None,
            playback_audio_size_bytes=(
                resolved_playback_record.audio_size_bytes if resolved_playback_record else None
            ),
        )

    def get_audio_history(self, device_id: str | None = None) -> VoiceNodeAudioHistoryResponse:
        resolved_device_id = self._resolve_device_id(device_id)
        with self._lock:
            records = tuple(self._audio_history.get(resolved_device_id, []))

        return VoiceNodeAudioHistoryResponse(
            device_id=resolved_device_id,
            items=[self._to_audio_history_item(record) for record in records],
        )

    def get_audio_report(self, device_id: str | None = None) -> VoiceNodeAudioReportResponse:
        resolved_device_id = self._resolve_device_id(device_id)
        with self._lock:
            records = tuple(self._audio_history.get(resolved_device_id, []))

        total_items = len(records)
        stt_success_count = sum(1 for record in records if record.stt_ok)
        blank_heard_count = sum(1 for record in records if not record.data.heard_text.strip())
        keep_mic_open_count = sum(1 for record in records if record.data.keep_mic_open)
        fallback_count = sum(1 for record in records if record.data.source == "fallback")
        scored_values = [
            record.stt_similarity
            for record in records
            if record.stt_similarity is not None
        ]
        playback_records = [
            record.playback_record
            for record in records
            if record.playback_record is not None
        ]
        playback_success_count = sum(
            1 for playback_record in playback_records if playback_record and playback_record.ok
        )
        duration_values = [
            record.audio_metrics.duration_ms
            for record in records
            if record.audio_metrics.duration_ms is not None
        ]
        peak_values = [
            record.audio_metrics.peak_ratio
            for record in records
            if record.audio_metrics.peak_ratio is not None
        ]
        rms_values = [
            record.audio_metrics.rms_ratio
            for record in records
            if record.audio_metrics.rms_ratio is not None
        ]
        audio_quality_ok_count = sum(1 for record in records if record.audio_metrics.quality == "ok")
        quiet_warning_count = sum(1 for record in records if record.audio_metrics.quality == "too_quiet")
        clipping_warning_count = sum(1 for record in records if record.audio_metrics.quality == "clipped")
        average_similarity = (
            round(sum(scored_values) / len(scored_values), 3) if scored_values else None
        )
        audio_quality_ok_rate = self._safe_ratio(audio_quality_ok_count, total_items)
        ready_for_demo = (
            total_items >= 5
            and self._safe_ratio(stt_success_count, total_items) >= 0.8
            and blank_heard_count == 0
            and (average_similarity is None or average_similarity >= 0.7)
            and self._safe_ratio(fallback_count, total_items) <= 0.2
            and (not peak_values or audio_quality_ok_rate >= 0.7)
            and (
                not playback_records
                or self._safe_ratio(playback_success_count, len(playback_records)) >= 0.8
            )
        )

        return VoiceNodeAudioReportResponse(
            device_id=resolved_device_id,
            generated_at=datetime.now(timezone.utc),
            total_items=total_items,
            stt_success_count=stt_success_count,
            stt_success_rate=self._safe_ratio(stt_success_count, total_items),
            blank_heard_count=blank_heard_count,
            scored_count=len(scored_values),
            average_similarity=average_similarity,
            high_score_count=sum(1 for score in scored_values if score >= 0.7),
            low_score_count=sum(1 for score in scored_values if score < 0.7),
            keep_mic_open_count=keep_mic_open_count,
            fallback_count=fallback_count,
            playback_success_count=playback_success_count,
            playback_success_rate=self._safe_ratio(playback_success_count, len(playback_records)),
            average_uploaded_duration_ms=(
                round(sum(duration_values) / len(duration_values)) if duration_values else None
            ),
            average_peak_ratio=(
                round(sum(peak_values) / len(peak_values), 3) if peak_values else None
            ),
            average_rms_ratio=(
                round(sum(rms_values) / len(rms_values), 3) if rms_values else None
            ),
            audio_quality_ok_count=audio_quality_ok_count,
            audio_quality_ok_rate=audio_quality_ok_rate,
            quiet_warning_count=quiet_warning_count,
            clipping_warning_count=clipping_warning_count,
            latest_received_at=records[0].received_at if records else None,
            ready_for_demo=ready_for_demo,
            notes=self._build_report_notes_v2(
                total_items=total_items,
                stt_success_count=stt_success_count,
                blank_heard_count=blank_heard_count,
                scored_count=len(scored_values),
                average_similarity=average_similarity,
                keep_mic_open_count=keep_mic_open_count,
                fallback_count=fallback_count,
                playback_records_count=len(playback_records),
                playback_success_count=playback_success_count,
                quiet_warning_count=quiet_warning_count,
                clipping_warning_count=clipping_warning_count,
                audio_quality_ok_rate=audio_quality_ok_rate,
            ),
        )

    def clear_audio_history(self, device_id: str | None = None) -> VoiceNodeAudioHistoryClearResponse:
        resolved_device_id = self._resolve_device_id(device_id)
        with self._lock:
            had_history = bool(
                self._audio_history.get(resolved_device_id)
                or self._latest_audio.get(resolved_device_id)
                or self._latest_playback.get(resolved_device_id)
                or self._commands.get(resolved_device_id)
            )
            cleared_pending_command_count = len(self._commands.get(resolved_device_id, []))
            self._audio_history.pop(resolved_device_id, None)
            self._latest_audio.pop(resolved_device_id, None)
            self._latest_playback.pop(resolved_device_id, None)
            self._active_expected_text.pop(resolved_device_id, None)
            self._commands.pop(resolved_device_id, None)
        return VoiceNodeAudioHistoryClearResponse(
            device_id=resolved_device_id,
            cleared=had_history,
            cleared_pending_command_count=cleared_pending_command_count,
        )

    def get_uploaded_audio(
        self,
        device_id: str | None = None,
    ) -> tuple[bytes, str, datetime] | None:
        resolved_device_id = self._resolve_device_id(device_id)
        with self._lock:
            record = self._latest_audio.get(resolved_device_id)

        if record is None:
            return None
        return (
            record.uploaded_audio_bytes,
            record.uploaded_audio_content_type,
            record.received_at,
        )

    def to_voice_node_audio_url(self, audio_url: str | None) -> str | None:
        if audio_url is None:
            return None
        return audio_url.replace("/voice/audio/current", "/voice-node/audio/current", 1)

    def _resolve_device_id(self, device_id: str | None) -> str:
        cleaned_device_id = (device_id or "").strip()
        return cleaned_device_id or self._settings.voice_node_default_id

    def _get_runtime_config(self, device_id: str) -> VoiceNodeRuntimeConfig:
        with self._lock:
            return self._runtime_config.get(device_id, VoiceNodeRuntimeConfig())

    @staticmethod
    def _value_or_default(value, default):
        return default if value is None else value

    @staticmethod
    def _optional_update(new_value, current_value):
        return current_value if new_value is None else new_value

    def _pending_command_count_unlocked(self, device_id: str) -> int:
        return len(self._commands.get(device_id, []))

    def _drop_expired_commands_unlocked(self, device_id: str) -> int:
        queue = self._commands.get(device_id)
        if not queue:
            return 0

        ttl_seconds = max(5, self._settings.voice_node_command_ttl_seconds)
        now = datetime.now(timezone.utc)
        fresh_queue = [
            command
            for command in queue
            if (now - command.created_at).total_seconds() <= ttl_seconds
        ]
        expired_queue = [
            command
            for command in queue
            if (now - command.created_at).total_seconds() > ttl_seconds
        ]
        dropped_count = len(queue) - len(fresh_queue)
        if dropped_count:
            if any(command.type == "conversation_start" for command in expired_queue):
                self._conversation_mode_enabled[device_id] = False
                self._conversation_mode_started_at.pop(device_id, None)
            if any(command.type == "wake_listen_start" for command in expired_queue):
                self._wake_mode_enabled[device_id] = False
                self._wake_conversation_active[device_id] = False
            if fresh_queue:
                self._commands[device_id] = fresh_queue
            else:
                self._commands.pop(device_id, None)
                self._active_expected_text.pop(device_id, None)
        return dropped_count

    def _reconcile_stale_modes_unlocked(
        self,
        device_id: str,
        board_state: str,
        now: datetime,
    ) -> bool:
        if not self._conversation_mode_enabled.get(device_id, False):
            return False
        if board_state != "WAKE_LISTENING":
            return False
        if self._commands.get(device_id):
            return False

        started_at = self._conversation_mode_started_at.get(device_id)
        latest_audio = self._latest_audio.get(device_id)
        reference_at = latest_audio.received_at if latest_audio is not None else started_at
        if reference_at is None:
            self._conversation_mode_started_at[device_id] = now
            return False

        stale_after_seconds = max(25, int(self._settings.voice_node_timeout_seconds))
        if (now - reference_at).total_seconds() < stale_after_seconds:
            return False

        self._conversation_mode_enabled[device_id] = False
        self._conversation_mode_started_at.pop(device_id, None)
        self._wake_conversation_active[device_id] = False
        self._auto_wake_suspended[device_id] = True
        self._pending_conversation_timeout_notice[device_id] = now
        return True

    def _ensure_auto_wake_unlocked(self, device_id: str) -> bool:
        if not self._settings.voice_node_enabled or not self._settings.voice_node_auto_wake_enabled:
            return False
        if self._auto_wake_suspended.get(device_id, False):
            return False

        self._drop_expired_commands_unlocked(device_id)
        if self._commands.get(device_id):
            return False
        if self._conversation_mode_enabled.get(device_id, False):
            return False
        if self._wake_conversation_active.get(device_id, False):
            return False

        if self._wake_mode_enabled.get(device_id, False):
            refresh_seconds = max(15, self._settings.voice_node_auto_wake_refresh_seconds)
            last_auto_wake_at = self._last_auto_wake_at.get(device_id)
            if (
                last_auto_wake_at is not None
                and (datetime.now(timezone.utc) - last_auto_wake_at).total_seconds() < refresh_seconds
            ):
                return False

        self._append_wake_start_command_unlocked(device_id)
        return True

    def _append_wake_start_command_unlocked(self, device_id: str) -> None:
        record = VoiceNodeCommandRecord(
            command_id=uuid4().hex,
            device_id=device_id,
            type="wake_listen_start",
            created_at=datetime.now(timezone.utc),
        )
        self._wake_mode_enabled[device_id] = True
        self._wake_conversation_active[device_id] = False
        self._last_auto_wake_at[device_id] = record.created_at
        self._commands.setdefault(device_id, []).append(record)

    @staticmethod
    def _to_command_data(record: VoiceNodeCommandRecord) -> VoiceNodeCommandData:
        return VoiceNodeCommandData(
            command_id=record.command_id,
            type=record.type,
            created_at=record.created_at,
            audio_url=record.audio_url,
            expected_text=record.expected_text,
        )

    def _to_audio_history_item(self, record: VoiceNodeAudioRecord) -> VoiceNodeAudioHistoryItem:
        data = record.data
        playback_record = record.playback_record
        metrics = record.audio_metrics
        return VoiceNodeAudioHistoryItem(
            received_at=record.received_at,
            server_received_at=record.server_received_at,
            server_processing_ms=self._duration_ms(record.server_received_at, record.received_at),
            playback_after_processing_ms=self._duration_ms(
                record.received_at,
                playback_record.reported_at if playback_record else None,
            ),
            seconds_since_received=self._seconds_since(record.received_at),
            stt_ok=record.stt_ok,
            stt_error=record.stt_error,
            stt_raw_text=record.stt_raw_text,
            expected_text=record.expected_text,
            stt_similarity=record.stt_similarity,
            heard_text=data.heard_text,
            reply=data.reply,
            intent=data.intent,
            source=data.source,
            action=data.action,
            keep_mic_open=data.keep_mic_open,
            uploaded_audio_size_bytes=len(record.uploaded_audio_bytes),
            uploaded_audio_duration_ms=metrics.duration_ms,
            uploaded_audio_peak_ratio=metrics.peak_ratio,
            uploaded_audio_rms_ratio=metrics.rms_ratio,
            uploaded_audio_clipping_ratio=metrics.clipping_ratio,
            uploaded_audio_quality=metrics.quality,
            uploaded_audio_quality_notes=list(metrics.quality_notes),
            playback_stage=playback_record.stage if playback_record else None,
            playback_ok=playback_record.ok if playback_record else None,
            playback_error=playback_record.error if playback_record else None,
            playback_audio_size_bytes=(
                playback_record.audio_size_bytes if playback_record else None
            ),
        )

    @staticmethod
    def _seconds_since(timestamp: datetime) -> int:
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return max(0, int((datetime.now(timezone.utc) - timestamp).total_seconds()))

    @staticmethod
    def _duration_ms(start: datetime | None, end: datetime | None) -> float | None:
        if start is None or end is None:
            return None
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        return round(max(0.0, (end - start).total_seconds() * 1000), 1)

    @staticmethod
    def _calculate_similarity(expected_text: str | None, heard_text: str) -> float | None:
        if not expected_text:
            return None
        normalized_expected = VoiceNodeManager._normalize_for_similarity(expected_text)
        normalized_heard = VoiceNodeManager._normalize_for_similarity(heard_text)
        if not normalized_expected or not normalized_heard:
            return 0.0
        raw_score = SequenceMatcher(None, normalized_expected, normalized_heard).ratio()
        if (
            ("เปิด" in normalized_expected and "ปิด" in normalized_heard)
            or ("ปิด" in normalized_expected and "เปิด" in normalized_heard)
        ):
            raw_score = min(raw_score, 0.55)
        boosted_score = VoiceNodeManager._keyword_similarity_boost(
            normalized_expected,
            normalized_heard,
        )
        return round(max(raw_score, boosted_score), 3)

    @staticmethod
    def _normalize_for_similarity(text: str) -> str:
        normalized = "".join(text.casefold().split())
        replacements = {
            "ไลน์": "line",
            "ให้หน่อย": "",
            "หน่อย": "",
            "ครับ": "",
            "ค่ะ": "",
            "คะ": "",
            "จ๊ะ": "",
            "จ้า": "",
        }
        for before, after in replacements.items():
            normalized = normalized.replace(before, after)
        return normalized

    @staticmethod
    def _keyword_similarity_boost(normalized_expected: str, normalized_heard: str) -> float:
        if normalized_expected in normalized_heard or normalized_heard in normalized_expected:
            shorter = min(len(normalized_expected), len(normalized_heard))
            longer = max(len(normalized_expected), len(normalized_heard))
            return max(0.72, shorter / longer)

        groups: tuple[tuple[tuple[str, ...], float], ...] = (
            (("ข่าว",), 0.45),
            (("line", "ส่งข่าว", "เข้ามือถือ"), 0.45),
            (("เปิด",), 0.35),
            (("ปิด",), 0.35),
            (("ไฟ", "หลอดไฟ", "รีเลย์"), 0.35),
            (("ร้อน", "อุณหภูมิ", "กี่องศา"), 0.35),
            (("ความชื้น",), 0.45),
            (("รถติด", "กรุงเทพ", "ยะลา"), 0.35),
            (("สนามบิน", "กี่นาที", "เวลา"), 0.35),
            (("สวัสดี", "น้องฟ้า"), 0.4),
        )
        expected_weights = [
            (terms, weight)
            for terms, weight in groups
            if any(term in normalized_expected for term in terms)
        ]
        if not expected_weights:
            return 0.0

        total_weight = sum(weight for _, weight in expected_weights)
        matched_weight = sum(
            weight
            for terms, weight in expected_weights
            if any(term in normalized_heard for term in terms)
        )
        if total_weight <= 0:
            return 0.0
        return min(0.95, matched_weight / total_weight)

    @staticmethod
    def _safe_ratio(numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round(numerator / denominator, 3)

    @staticmethod
    def _analyze_wav_audio(audio_bytes: bytes) -> VoiceNodeAudioMetrics:
        try:
            with wave.open(io.BytesIO(audio_bytes), "rb") as reader:
                channel_count = reader.getnchannels()
                sample_width = reader.getsampwidth()
                sample_rate = reader.getframerate()
                frame_count = reader.getnframes()
                frames = reader.readframes(frame_count)
        except wave.Error:
            return VoiceNodeAudioMetrics(
                duration_ms=VoiceNodeManager._wav_duration_ms(audio_bytes),
                quality="unknown",
                quality_notes=("not a readable wav file",),
            )

        bits_per_sample = sample_width * 8
        duration_ms = round((frame_count / sample_rate) * 1000) if sample_rate > 0 else None
        if sample_width != 2 or channel_count <= 0 or not frames:
            return VoiceNodeAudioMetrics(
                duration_ms=duration_ms,
                sample_rate_hz=sample_rate,
                channel_count=channel_count,
                bits_per_sample=bits_per_sample,
                quality="unknown",
                quality_notes=("unsupported wav format for diagnostics",),
            )

        samples = array("h")
        samples.frombytes(frames)
        if len(samples) == 0:
            return VoiceNodeAudioMetrics(
                duration_ms=duration_ms,
                sample_rate_hz=sample_rate,
                channel_count=channel_count,
                bits_per_sample=bits_per_sample,
                quality="too_quiet",
                quality_notes=("audio has no samples",),
            )

        peak = max(abs(sample) for sample in samples)
        sum_square = sum(float(sample) * float(sample) for sample in samples)
        rms = (sum_square / len(samples)) ** 0.5
        clipping_count = sum(1 for sample in samples if abs(sample) >= 32000)
        silence_threshold = max(120, round(32767 * 0.004))
        silence_count = sum(1 for sample in samples if abs(sample) <= silence_threshold)

        peak_ratio = round(peak / 32767, 3)
        rms_ratio = round(rms / 32767, 3)
        clipping_ratio = round(clipping_count / len(samples), 4)
        silence_ratio = round(silence_count / len(samples), 3)
        quality, notes = VoiceNodeManager._classify_audio_quality(
            duration_ms=duration_ms,
            peak_ratio=peak_ratio,
            rms_ratio=rms_ratio,
            clipping_ratio=clipping_ratio,
            silence_ratio=silence_ratio,
        )

        return VoiceNodeAudioMetrics(
            duration_ms=duration_ms,
            sample_rate_hz=sample_rate,
            channel_count=channel_count,
            bits_per_sample=bits_per_sample,
            peak_ratio=peak_ratio,
            rms_ratio=rms_ratio,
            clipping_ratio=clipping_ratio,
            silence_ratio=silence_ratio,
            quality=quality,
            quality_notes=tuple(notes),
        )

    @staticmethod
    def _classify_audio_quality(
        duration_ms: int | None,
        peak_ratio: float,
        rms_ratio: float,
        clipping_ratio: float,
        silence_ratio: float,
    ) -> tuple[str, list[str]]:
        notes: list[str] = []
        quality = "ok"

        if duration_ms is not None and duration_ms < 900:
            quality = "too_short"
            notes.append("recording is too short; wait for the cue beep, then speak")
        if peak_ratio < 0.06 or rms_ratio < 0.006 or silence_ratio > 0.97:
            quality = "too_quiet"
            notes.append("audio is too quiet; move closer to INMP441 or increase Mic gain in Voice Node Test")
        if clipping_ratio >= 0.01 or peak_ratio >= 0.98:
            quality = "clipped"
            notes.append(
                "audio is clipping; reduce Mic gain in Voice Node Test or move 20-30 cm from INMP441"
            )

        if not notes:
            notes.append("audio level looks usable")
        return quality, notes

    @staticmethod
    def _analyze_pcm16_chunk(chunk: bytes) -> tuple[float | None, float | None]:
        if len(chunk) < 2:
            return None, None
        even_length = len(chunk) - (len(chunk) % 2)
        samples = array("h")
        samples.frombytes(chunk[:even_length])
        if not samples:
            return None, None
        peak = max(abs(sample) for sample in samples)
        sum_square = sum(float(sample) * float(sample) for sample in samples)
        rms = (sum_square / len(samples)) ** 0.5
        return round(peak / 32767, 3), round(rms / 32767, 3)

    @staticmethod
    def _wav_duration_ms(audio_bytes: bytes) -> int | None:
        if len(audio_bytes) < 44 or audio_bytes[:4] != b"RIFF" or audio_bytes[8:12] != b"WAVE":
            return None

        offset = 12
        sample_rate: int | None = None
        channels: int | None = None
        bits_per_sample: int | None = None
        data_bytes: int | None = None

        while offset + 8 <= len(audio_bytes):
            chunk_id = audio_bytes[offset : offset + 4]
            chunk_size = int.from_bytes(audio_bytes[offset + 4 : offset + 8], "little")
            chunk_start = offset + 8
            if chunk_start + chunk_size > len(audio_bytes):
                break
            if chunk_id == b"fmt " and chunk_size >= 16:
                channels = int.from_bytes(audio_bytes[chunk_start + 2 : chunk_start + 4], "little")
                sample_rate = int.from_bytes(audio_bytes[chunk_start + 4 : chunk_start + 8], "little")
                bits_per_sample = int.from_bytes(audio_bytes[chunk_start + 14 : chunk_start + 16], "little")
            elif chunk_id == b"data":
                data_bytes = chunk_size
                break
            offset = chunk_start + chunk_size + (chunk_size % 2)

        if not sample_rate or not channels or not bits_per_sample or data_bytes is None:
            return None
        bytes_per_second = sample_rate * channels * (bits_per_sample // 8)
        if bytes_per_second <= 0:
            return None
        return round((data_bytes / bytes_per_second) * 1000)

    @staticmethod
    def _build_report_notes(
        total_items: int,
        stt_success_count: int,
        scored_count: int,
        average_similarity: float | None,
        playback_records_count: int,
        playback_success_count: int,
    ) -> list[str]:
        notes: list[str] = []
        if total_items == 0:
            return ["ยังไม่มีข้อมูลทดสอบจากบอร์ด"]
        if total_items < 5:
            notes.append("ควรเทสอย่างน้อย 5 รอบก่อนตัดสินความพร้อม")
        if stt_success_count < total_items:
            notes.append("มีบางรอบที่ STT ยังไม่เจอเสียงพูด")
        if scored_count == 0:
            notes.append("ยังไม่มีรอบที่เลือกประโยคทดสอบเพื่อวัดคะแนน")
        elif average_similarity is not None and average_similarity < 0.7:
            notes.append("คะแนน STT เฉลี่ยยังต่ำกว่า 70% ควรขยับไมค์หรือปรับ gain/VAD")
        if playback_records_count > 0 and playback_success_count < playback_records_count:
            notes.append("มีบางรอบที่บอร์ดรายงาน playback ไม่สำเร็จ")
        if not notes:
            notes.append("ผลรวมดูพร้อมสำหรับเดโมรอบแรก")
        return notes


    @staticmethod
    def _build_report_notes_v2(
        total_items: int,
        stt_success_count: int,
        blank_heard_count: int,
        scored_count: int,
        average_similarity: float | None,
        keep_mic_open_count: int,
        fallback_count: int,
        playback_records_count: int,
        playback_success_count: int,
        quiet_warning_count: int,
        clipping_warning_count: int,
        audio_quality_ok_rate: float,
    ) -> list[str]:
        notes: list[str] = []
        if total_items == 0:
            return ["No voice-node test data yet"]
        if total_items < 5:
            notes.append("Run at least 5 rounds before judging demo readiness")
        if stt_success_count < total_items:
            notes.append("Some rounds did not produce speech text")
        if blank_heard_count > 0:
            notes.append(f"{blank_heard_count} round(s) had blank heard text")
        if total_items >= 3 and keep_mic_open_count == 0:
            notes.append("No recent round kept the board mic open; test continuous conversation mode")
        if fallback_count > 0:
            notes.append(f"{fallback_count} round(s) used fallback response")
        if scored_count == 0:
            notes.append("No scored rounds yet; choose a test sentence before recording")
        elif average_similarity is not None and average_similarity < 0.7:
            notes.append("Average STT score is below 70%; check mic distance, gain, or VAD")
        if quiet_warning_count > 0:
            notes.append(f"{quiet_warning_count} round(s) look too quiet")
        if clipping_warning_count > 0:
            notes.append(
                f"{clipping_warning_count} round(s) clipped; reduce Mic gain in Voice Node Test or move farther from the mic"
            )
        if total_items >= 5 and audio_quality_ok_rate < 0.7:
            notes.append("Audio quality is unstable; inspect per-round peak/RMS details")
        if playback_records_count > 0 and playback_success_count < playback_records_count:
            notes.append("Some rounds reported playback failure")
        if not notes:
            notes.append("Overall result looks ready for a first demo")
        return notes


_voice_node_manager = VoiceNodeManager(get_settings())


def get_voice_node_manager() -> VoiceNodeManager:
    return _voice_node_manager
