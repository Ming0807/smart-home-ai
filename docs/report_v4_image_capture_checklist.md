# Report V4 Image Capture Checklist

Use this checklist before replacing the remaining screenshot/photo placeholders in `report_AI_Smart_Home_Thai_Assistant_aligned_v4.docx`.

## Must Not Be Missing

- System Architecture Diagram
- DFD / Data Flow Diagram
- Control Node Flowchart
- Voice Node Flowchart / State Machine
- Wiring Diagram / Pinout
- UX/UI Dashboard Screenshot
- Chat Result Screenshots
- Relay Control Panel Screenshot
- Sensor Panel Screenshot
- Voice Node Test Panel Screenshot
- Device Registry Panel Screenshot
- Real Hardware Photos

## Screenshots To Capture From Web UI

### 1. Full Dashboard

Capture the whole dashboard at `http://localhost:8000`.

Must show:

- ESP32/LLM/Voice Node status.
- Chat panel.
- Sensor/relay/voice/device sections.
- Current real demo data.

### 2. Chat Examples

Capture several real chat examples.

Recommended prompts:

- `สวัสดี`
- `ห้องร้อนไหม`
- `เปิดไฟห้องนอน`
- `ปิดไฟห้องครัว`
- `ข้างนอกร้อนไหม`
- `ข่าววันนี้มีอะไร`
- `ในกรุงเทพรถติดไหม`

Must show:

- AI reply.
- intent/source badges.
- audio status if available.

### 3. Relay Control Panel

Must show all four relay channels:

- Relay 1: Living Room Light, GPIO5.
- Relay 2: Bedroom Light, GPIO7.
- Relay 3: Bathroom Light, GPIO8.
- Relay 4: Kitchen Light, GPIO9.

Also show latest command/status after testing at least one on/off command.

### 4. Sensor Panel

Must show:

- DHT22 temperature.
- DHT22 humidity.
- Last updated time.
- PIR motion state.
- ESP32 online/heartbeat status.

Important: if DHT22 is physically wired to GPIO4 instead of GPIO14, update the report, firmware config, and registry before final submission.

### 5. Voice Node Test Panel

Must show:

- `voice-node-01` online.
- IP address and current state.
- Last uploaded audio / file size.
- STT heard text and score.
- Playback success/status.
- Recent test history.

### 6. Device Registry Panel

Must show:

- `relay_1` to `relay_4`.
- Room names, relay channel, GPIO pin, enabled state.
- `dht22_1` and `pir_1`.
- Add/edit device form if possible.

## Real Photos To Take

### Control Node Photo

Take a clear photo of:

- ESP32-S3 Control Node.
- DHT22.
- PIR HC-SR501.
- 4-channel relay module.
- Jumper wires and power/GND.

### Voice Node Photo

Take a clear photo of:

- ESP32-S3 Voice Node.
- INMP441 microphone.
- MAX98357A amplifier.
- Speaker.
- Power wiring and common ground.

### Demo Setup Photo

Take a wider photo showing:

- Laptop/server.
- Web dashboard.
- ESP32 Control Node.
- ESP32 Voice Node.
- Speaker/microphone area.

## Final Visual QA

- No old mockup image should remain in Chapter 4.
- No image should mention Typhoon as the current primary model unless it is explicitly described as optional/previous.
- No image should show Relay 1 only.
- No image should show a separate ESP32 Sensor Node.
- No image should expose API keys, tokens, Wi-Fi passwords, or secrets.
- Figure captions must match the actual image content.
