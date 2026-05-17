# Voice Node Streaming Upgrade Plan

## Goal

Improve Thai STT quality from the ESP32-S3 Voice Node by moving heavier audio decisions to the local server while preserving the current working browser mic and multipart WAV upload paths.

## Non-Negotiables

- Do not break Browser Mic.
- Do not remove the current `/assistant/audio` multipart upload path.
- Do not replace the current Voice Node wake mode until streaming is tested.
- Keep all streaming work opt-in and reversible.
- Prefer ESP-IDF over Arduino for this project because the current firmware is already stable.

## Recommended Architecture

```text
INMP441
  -> ESP32-S3 I2S PCM 16 kHz / 16-bit / mono
  -> WebSocket binary stream
  -> FastAPI streaming endpoint
  -> server-side audio diagnostics
  -> server-side VAD
  -> optional noise reduction
  -> Faster-Whisper STT
  -> existing chat pipeline
  -> existing TTS WAV playback path
```

## Ordered Work

### Phase S0 - Streaming Diagnostics Foundation

- [x] Keep current multipart Voice Node flow unchanged.
- [x] Add WebSocket endpoint for raw PCM frames.
- [x] Add in-memory stream status metrics.
- [x] Add Web UI diagnostics: connected, bytes, frames, peak, RMS, estimated audio seconds.
- [x] Validate with a simple local WebSocket client before touching firmware.

### Phase S1 - Firmware PCM Stream Proof

- [x] Add firmware command `stream_test_start`.
- [x] ESP32 sends short PCM stream to server for 5-10 seconds.
- [x] Server receives frames and updates diagnostics.
- [x] No STT yet.
- [x] Keep existing record-once / wake mode buttons working.
- [x] Flash and verify on real `voice-node-01`.

### Phase S2 - Server VAD

- [x] Add lightweight server-side VAD boundary detection.
- [x] Start with RMS/silence gate.
- [x] Add smoothing: require stable speech/silence frames before changing utterance state.
- [x] Tune default RMS threshold to reduce false speech in a quiet room.
- [ ] Add WebRTC VAD only if needed.
- [ ] Keep Silero VAD as optional later dependency.

### Phase S3 - Streaming STT

- [x] Add opt-in WebSocket processing path with `process=true`.
- [x] Buffer PCM stream on server.
- [x] Convert PCM buffer to WAV in memory.
- [x] Reuse existing assistant audio pipeline for STT -> chat -> TTS.
- [ ] Add firmware/UI command for streaming STT test after diagnostic mode remains stable.

### Phase S4 - Noise Reduction / Preprocessing

- [x] Start with safe CPU-light preprocessing: trim quiet edges and normalize PCM stream before STT.
- [ ] Validate with 5-10 real speech rounds from the INMP441.
- [ ] Evaluate `noisereduce` if static hum remains.
- [ ] Evaluate DeepFilterNet only after baseline streaming is stable.

### Phase S5 - Production Voice Node Mode

- [ ] Replace fixed 6-second upload with streaming mode only after tests pass.
- [ ] Keep multipart upload as fallback.
- [ ] Add UI switch: `Upload Mode` / `Streaming Mode`.

## Current Best Next Step

Implement Phase S1 next. The server can now receive diagnostic PCM frames safely without changing the current firmware upload flow.
