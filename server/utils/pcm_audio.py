from __future__ import annotations

import io
import math
import wave
from array import array


def pcm16_to_wav_bytes(
    pcm_bytes: bytes,
    sample_rate_hz: int,
    channels: int = 1,
) -> bytes:
    """Wrap little-endian PCM16 bytes in a WAV container."""
    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(max(1, channels))
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate_hz)
        wav_file.writeframes(pcm_bytes)
    return output.getvalue()


def prepare_pcm16_for_stt(
    pcm_bytes: bytes,
    sample_rate_hz: int,
    vad_rms_threshold: float,
    trim_padding_ms: int = 250,
    target_peak: float = 0.82,
    max_gain: float = 3.0,
) -> bytes:
    """Trim quiet edges and gently normalize PCM16 mono audio before STT."""
    if not pcm_bytes or sample_rate_hz <= 0:
        return pcm_bytes

    even_length = len(pcm_bytes) - (len(pcm_bytes) % 2)
    if even_length <= 0:
        return b""

    samples = array("h")
    samples.frombytes(pcm_bytes[:even_length])
    if not samples:
        return pcm_bytes[:even_length]

    trimmed = _trim_pcm16_silence(
        samples=samples,
        sample_rate_hz=sample_rate_hz,
        vad_rms_threshold=vad_rms_threshold,
        trim_padding_ms=trim_padding_ms,
    )
    normalized = _normalize_pcm16(
        samples=trimmed,
        target_peak=target_peak,
        max_gain=max_gain,
    )
    return normalized.tobytes()


def _trim_pcm16_silence(
    samples: array,
    sample_rate_hz: int,
    vad_rms_threshold: float,
    trim_padding_ms: int,
) -> array:
    window_samples = max(160, sample_rate_hz // 50)  # roughly 20 ms at 16 kHz
    threshold = max(0.001, min(0.5, vad_rms_threshold))
    speech_windows: list[tuple[int, int]] = []

    for start in range(0, len(samples), window_samples):
        end = min(len(samples), start + window_samples)
        if end <= start:
            continue
        if _rms_ratio(samples[start:end]) >= threshold:
            speech_windows.append((start, end))

    if not speech_windows:
        return samples

    padding_samples = max(0, int(sample_rate_hz * max(0, trim_padding_ms) / 1000))
    trim_start = max(0, speech_windows[0][0] - padding_samples)
    trim_end = min(len(samples), speech_windows[-1][1] + padding_samples)
    if trim_end <= trim_start:
        return samples
    return samples[trim_start:trim_end]


def _normalize_pcm16(
    samples: array,
    target_peak: float,
    max_gain: float,
) -> array:
    peak = max((abs(sample) for sample in samples), default=0)
    if peak <= 0:
        return samples

    bounded_target_peak = max(0.1, min(0.98, target_peak))
    bounded_max_gain = max(1.0, min(10.0, max_gain))
    target = int(32767 * bounded_target_peak)
    gain = min(bounded_max_gain, target / peak)
    if gain <= 1.03:
        return samples

    output = array("h")
    for sample in samples:
        value = int(sample * gain)
        if value > 32767:
            value = 32767
        elif value < -32768:
            value = -32768
        output.append(value)
    return output


def _rms_ratio(samples: array) -> float:
    if not samples:
        return 0.0
    mean_square = sum(sample * sample for sample in samples) / len(samples)
    return min(1.0, math.sqrt(mean_square) / 32768.0)
