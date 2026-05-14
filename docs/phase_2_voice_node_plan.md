# Phase 2 Voice / Wake Word Node Plan

## 1. เป้าหมาย

Phase 2 คือการเพิ่ม ESP32-S3 N16R8 ตัวที่ 2 เป็น Voice / Wake Word Node โดยไม่กระทบ Phase 1 ที่ทำงานนิ่งแล้ว

Phase 1 ยังเป็นฐานหลัก:

- `esp32-01` เป็น Control Node
- ใช้ MicroPython
- อ่าน DHT22
- อ่าน PIR Motion
- ควบคุม relay
- ส่ง heartbeat / sensor / motion ไป FastAPI
- รับคำสั่ง relay จาก FastAPI
- Web UI และ browser mic ยังใช้งานได้เหมือนเดิม

Phase 2 เป็นช่องทางเสียงเสริม:

- `voice-node-01` เป็น Voice Node
- ใช้ ESP-IDF + ESP-SR
- ฟัง wake word
- อัดเสียงจาก INMP441
- ส่งเสียงไป FastAPI
- รับเสียงตอบกลับจาก FastAPI
- เล่นเสียงผ่าน MAX98357A + speaker

หลักสำคัญ: ถ้า Voice Node มีปัญหา Phase 1 ต้องยังใช้งานได้ครบผ่าน Web UI / browser mic / Control Node

---

## 2. สถาปัตยกรรมเป้าหมาย

```text
[Browser / Mobile Web]
  - chat
  - browser mic
  - dashboard
  - debug mode

        |
        v

[FastAPI Server]
  - /chat
  - /voice/chat
  - /assistant/audio
  - STT
  - Intent Router
  - LLM
  - TTS
  - Device Manager

        |
        +---------------------> [ESP32-S3 Control Node: esp32-01]
        |                         - MicroPython
        |                         - DHT22
        |                         - PIR
        |                         - Relay
        |
        +<--------------------> [ESP32-S3 Voice Node: voice-node-01]
                                  - ESP-IDF / ESP-SR
                                  - INMP441 mic
                                  - MAX98357A amp
                                  - Speaker
                                  - Wake word
```

---

## 3. ขอบเขตที่ห้ามกระทบ

ห้ามเปลี่ยนพฤติกรรมเดิมของ:

- `POST /chat`
- `POST /voice/chat`
- `POST /voice/speak`
- `POST /esp32/heartbeat`
- `POST /esp32/sensor`
- `POST /esp32/motion`
- `GET /esp32/commands`
- Web UI browser mic
- Device Registry
- Control Node MicroPython

Phase 2 ต้องเพิ่ม endpoint / service ใหม่แบบ opt-in เท่านั้น

---

## 4. Hardware ของ Voice Node

ใช้บอร์ด:

- ESP32-S3 N16R8
- INMP441 I2S microphone
- MAX98357A I2S amplifier
- Speaker 4 ohm 3W
- ESP32-S3 GPIO expansion board
- Adapter 9V 2A

ข้อควรระวัง:

- ห้ามป้อน 9V เข้า ESP32 หรือ MAX98357A โดยตรง ถ้าโมดูลไม่ได้รองรับ
- MAX98357A โดยทั่วไปใช้ 3.3V หรือ 5V ตามโมดูล
- Speaker 4 ohm 3W ควรใช้ไฟเลี้ยง amp ที่พอ ไม่ดึงจาก 3.3V ของ ESP32
- ทุกโมดูลต้อง common GND
- ตรวจ pin จริงกับบอร์ดขยายก่อน flash firmware

---

## 5. Wiring แนะนำเริ่มต้น

แยก I2S input และ output คนละชุดก่อน เพื่อ debug ง่ายและลด clock/audio conflict

### INMP441 Microphone

```text
INMP441 VDD -> 3.3V
INMP441 GND -> GND
INMP441 WS  -> GPIO16
INMP441 SCK -> GPIO17
INMP441 SD  -> GPIO18
INMP441 L/R -> GND
```

### MAX98357A Amplifier

```text
MAX98357A VIN  -> 5V หรือ 3.3V ตามโมดูล
MAX98357A GND  -> GND
MAX98357A LRC  -> GPIO9
MAX98357A BCLK -> GPIO10
MAX98357A DIN  -> GPIO11
Speaker +      -> SPK+
Speaker -      -> SPK-
```

หมายเหตุ: GPIO ชุดนี้เป็นค่าเริ่มต้นสำหรับทดลอง ต้องยืนยันกับบอร์ดจริงก่อนใช้งาน

---

## 6. Firmware Strategy

ใช้ ESP-IDF + ESP-SR สำหรับ Voice Node

เหตุผล:

- ESP-SR มี WakeNet สำหรับ wake word
- ESP-SR มี AFE / VAD ที่เหมาะกับเสียงบน ESP32-S3
- เหมาะกับงาน wake word มากกว่า MicroPython
- MicroPython ยังอยู่กับ Control Node ต่อไป ไม่ต้องย้าย

เริ่มด้วย wake word สำเร็จรูปก่อน:

- `Hi ESP`

อย่าเริ่มจาก wake word ไทยทันที เพราะ custom wake word อาจใช้เวลาและเสี่ยงทำให้ milestone แรกช้า

---

## 7. Audio Format

รูปแบบเสียงมาตรฐานของ Phase 2:

```text
sample_rate: 16000 Hz
bit_depth: 16-bit signed PCM
channels: mono
upload_format: WAV preferred, raw PCM optional
playback_format: WAV/PCM from server preferred
```

หลักสำคัญ:

- Voice Node ไม่ควร decode MP3 ใน milestone แรก
- Browser ยังใช้ MP3 ได้เหมือนเดิม
- FastAPI ควรมี output สำหรับ Voice Node เป็น WAV/PCM เพื่อลดภาระ ESP32

---

## 8. Voice Node State Machine

```text
BOOT
  -> WIFI_CONNECTING
  -> REGISTERING
  -> WAKE_LISTENING
  -> WAKE_DETECTED
  -> BEEPING
  -> RECORDING_COMMAND
  -> UPLOADING_AUDIO
  -> WAITING_SERVER_REPLY
  -> PLAYING_REPLY
  -> COOLDOWN
  -> WAKE_LISTENING

ERROR
  -> retry with backoff
  -> WAKE_LISTENING when recovered
```

กฎสำคัญ:

- ระหว่าง `PLAYING_REPLY` ต้อง mute mic / pause wake detection
- หลังเล่นเสียงจบ ให้หน่วง 300-500 ms ก่อนกลับไปฟัง wake word
- ถ้า upload ล้มเหลว ให้ beep error สั้น ๆ แล้วกลับไป `WAKE_LISTENING`
- ห้ามเขียน audio ลง Flash ใน loop ปกติ ใช้ RAM/PSRAM buffer

---

## 9. Backend Contract ที่ควรเพิ่ม

เพิ่ม endpoint ใหม่ ไม่แก้ endpoint เดิม

### `POST /voice-node/heartbeat`

ใช้บอกว่า Voice Node ยัง online

Request:

```json
{
  "device_id": "voice-node-01",
  "firmware_version": "0.1.0",
  "state": "WAKE_LISTENING",
  "ip_address": "192.168.1.80"
}
```

Response:

```json
{
  "status": "ok",
  "server_time": "2026-05-06T12:00:00+07:00"
}
```

### `GET /voice-node/config`

ให้บอร์ดดึง config ที่จำเป็น

Response:

```json
{
  "device_id": "voice-node-01",
  "enabled": true,
  "wake_word": "Hi ESP",
  "record_seconds": 4,
  "sample_rate": 16000,
  "audio_format": "wav",
  "reply_audio_format": "wav",
  "server_audio_endpoint": "/assistant/audio"
}
```

### `POST /assistant/audio`

รับเสียงจาก Voice Node แล้ววิ่งเข้า pipeline เดิม

Request:

- multipart/form-data
- field `audio`
- field `device_id`
- optional field `pir_state`
- optional field `source=voice_node`

Response:

```json
{
  "status": "success",
  "data": {
    "heard_text": "เปิดไฟให้หน่อย",
    "reply": "ส่งคำสั่งเปิดไฟให้แล้ว กำลังรอ ESP32 ยืนยันผล",
    "intent": "device_control",
    "source": "device_control",
    "action": "light_on",
    "reply_audio_url": "/voice-node/audio/current.wav",
    "reply_audio_format": "wav"
  }
}
```

### `GET /voice-node/audio/current.wav`

ใช้ให้บอร์ดดาวน์โหลดเสียงตอบกลับ

ข้อกำหนด:

- WAV/PCM 16 kHz 16-bit mono
- เขียนทับไฟล์เดิมได้
- มี token/version กัน cache ถ้าจำเป็น

---

## 10. Config ที่ควรเพิ่มใน FastAPI

ค่าเริ่มต้นควรไม่กระทบระบบเดิม

```env
VOICE_NODE_ENABLED=true
VOICE_NODE_DEFAULT_ID=voice-node-01
VOICE_NODE_WAKE_WORD=Hi ESP
VOICE_NODE_AUDIO_FORMAT=wav
VOICE_NODE_REPLY_AUDIO_FORMAT=mp3
VOICE_NODE_SAMPLE_RATE=16000
VOICE_NODE_RECORD_SECONDS=4
VOICE_NODE_TIMEOUT_SECONDS=30
VOICE_NODE_HEARTBEAT_TIMEOUT_SECONDS=60
```

หมายเหตุ Phase 2A: ระบบตอบกลับเสียงจาก server ยังใช้ MP3 จาก Edge TTS เดิมก่อน เพื่อไม่เพิ่ม dependency แปลงไฟล์และไม่กระทบ browser voice เดิม ส่วน WAV/PCM สำหรับ MAX98357A ให้ทำใน Phase 2E ก่อนเริ่ม playback จริง

ถ้าต้องการปิด Voice Node ระหว่าง demo ให้ตั้ง `VOICE_NODE_ENABLED=false` โดยระบบ Phase 1 ต้องยังทำงานปกติ

---

## 11. Milestones

### Phase 2A: Backend Contract

เป้าหมาย:

- เพิ่ม model/config สำหรับ Voice Node
- เพิ่ม `/voice-node/heartbeat`
- เพิ่ม `/voice-node/config`
- เพิ่ม `/assistant/audio`
- เพิ่ม service แปลง TTS reply เป็น WAV/PCM สำหรับ Voice Node
- เทสด้วย curl / ไฟล์ wav จากเครื่องก่อน

ยังไม่ต้อง flash firmware จริง

เกณฑ์ผ่าน:

- Server import ผ่าน
- `/voice-node/config` ตอบได้
- upload wav เข้า `/assistant/audio` แล้วได้ `heard_text`, `reply`, `reply_audio_url`
- Browser voice เดิมยังทำงานเหมือนเดิม

### Phase 2B: ESP-IDF Skeleton

เป้าหมาย:

- สร้าง `firmware/voice_node_espidf/`
- Wi-Fi connect
- heartbeat ไป server
- state machine พื้นฐาน
- serial log อ่านง่าย

เกณฑ์ผ่าน:

- บอร์ดต่อ Wi-Fi ได้
- `/voice-node/heartbeat` เห็น online
- ไม่มี audio logic หนัก

สถานะเริ่มต้น:

- เพิ่ม skeleton project แล้วใน `firmware/voice_node_espidf/`
- ใช้ `idf.py menuconfig` ตั้ง Wi-Fi และ server URL
- ยังไม่เปิด INMP441 / MAX98357A / ESP-SR

### Phase 2C: INMP441 Mic Bring-up

เป้าหมาย:

- I2S mic อ่านเสียง 16 kHz 16-bit mono
- คำนวณ RMS/peak ผ่าน serial
- อัด buffer 3-4 วินาที
- upload audio ไป server

เกณฑ์ผ่าน:

- พูดแล้ว RMS เปลี่ยนชัดเจน
- server รับไฟล์เสียงได้
- STT ได้ข้อความพอใช้งาน

สถานะเริ่มต้น:

- เพิ่ม INMP441 RMS/peak test ใน `firmware/voice_node_espidf/`
- เปิด/ปิดผ่าน `idf.py menuconfig`
- ค่า pin เริ่มต้น: WS=GPIO16, SCK=GPIO17, SD=GPIO18, L/R=GND
- ยังไม่อัด WAV และยังไม่ upload audio ในรอบนี้

### Phase 2D: Wake Word

เป้าหมาย:

- เปิด ESP-SR / WakeNet
- ใช้ `Hi ESP`
- detect แล้ว beep/log
- detect แล้วเริ่ม record command

เกณฑ์ผ่าน:

- ปลุกได้จากระยะใช้งานจริง
- false wake ไม่ถี่เกิน
- หลัง wake แล้ว upload command ได้

### Phase 2E: MAX98357A Playback

เป้าหมาย:

- เล่น beep
- เล่น WAV/PCM จาก server
- mute mic ระหว่าง speaker เล่น

เกณฑ์ผ่าน:

- เสียงดังพอ
- ไม่เกิด feedback loop
- เล่นจบแล้วกลับ wake listening

### Phase 2F: Full Loop

เป้าหมาย:

- wake -> record -> STT -> chat -> TTS WAV -> play -> wake listening
- เพิ่ม retry/backoff
- เพิ่ม dashboard card สำหรับ Voice Node

เกณฑ์ผ่าน:

- ใช้งานต่อเนื่องได้หลายรอบ
- Phase 1 ยังทำงานครบ
- ถ้า Voice Node ล่ม Web UI ยังควบคุมบ้านได้

---

## 12. Test Plan

### Backend-only test

1. รัน FastAPI
2. เรียก `/voice-node/config`
3. ส่ง heartbeat ด้วย curl
4. upload wav ตัวอย่างเข้า `/assistant/audio`
5. ตรวจว่าได้ audio reply
6. เปิด Web UI แล้วทดสอบ browser mic เดิม

### Firmware test

1. Flash skeleton
2. ดู serial log
3. เช็ก heartbeat บน server
4. เช็ก mic RMS
5. เช็ก upload audio
6. เช็ก wake word
7. เช็ก speaker playback

### End-to-end test

1. พูด `Hi ESP`
2. ได้ beep
3. พูด `เปิดไฟให้หน่อย`
4. Server แปลงเสียงเป็น text
5. Server สร้าง relay command ให้ `esp32-01`
6. Control Node รับคำสั่งและ apply relay
7. Voice Node เล่นเสียงตอบกลับ
8. กลับไปรอฟัง wake word

---

## 13. Risks และแนวทางลดความเสี่ยง

### Risk: Wake word ไทยทำยาก

แนวทาง:

- เริ่มด้วย `Hi ESP`
- เก็บ custom wake word ไทยไว้ Phase 2.2

### Risk: MP3 playback บน ESP32 ซับซ้อน

แนวทาง:

- ให้ server สร้าง WAV/PCM สำหรับ Voice Node
- Browser ยังใช้ MP3 ได้เหมือนเดิม

### Risk: Speaker feedback เข้า mic

แนวทาง:

- mute mic ตอน playback
- หน่วง 300-500 ms หลัง playback
- วาง mic ห่างจาก speaker
- ลด gain/volume ในรอบแรก

### Risk: Firmware ใช้เวลามาก

แนวทาง:

- แยกเป็น skeleton, mic, wake, speaker, full loop
- ห้ามทำทุกอย่างพร้อมกัน

### Risk: Phase 1 พัง

แนวทาง:

- เพิ่ม endpoint ใหม่เท่านั้น
- ใช้ `VOICE_NODE_ENABLED=false` เพื่อปิด Voice Node ได้ทันทีถ้าต้อง isolate Phase 1
- ห้ามเปลี่ยน `/chat`, `/voice/chat`, `/esp32/*` ที่มีอยู่โดยไม่จำเป็น

---

## 14. Definition of Done สำหรับ Phase 2 รอบแรก

Phase 2 รอบแรกถือว่าสำเร็จเมื่อ:

- Control Node ยังทำงานครบ
- Web UI browser mic ยังทำงานครบ
- Voice Node ปลุกด้วย `Hi ESP` ได้
- Voice Node อัดเสียงคำสั่งได้
- Server แปลงเสียงเป็นข้อความได้
- Server วิเคราะห์คำสั่งผ่าน pipeline เดิมได้
- Voice Node เล่นเสียงตอบกลับได้
- หลังตอบกลับแล้วกลับไปฟัง wake word ใหม่

---

## 15. แผนเริ่มงานถัดไป

ลำดับที่แนะนำ:

1. เทส patch ล่าสุดของ Phase 1 ให้ผ่าน
2. Commit baseline ของ Phase 1
3. เริ่ม Phase 2A: Backend Contract
4. เทส `/voice-node/config` และ `/voice-node/heartbeat`
5. เพิ่ม `/assistant/audio`
6. เทส upload wav จากเครื่องก่อน
7. ค่อยเริ่ม ESP-IDF skeleton
