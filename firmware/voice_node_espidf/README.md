# ESP32-S3 Voice Node Firmware

Firmware นี้เป็น Phase 2B/2C สำหรับ ESP32-S3 N16R8 ตัวที่ 2 เท่านั้น

เป้าหมายรอบนี้:

- ต่อ Wi-Fi
- อ่าน config จาก FastAPI `/voice-node/config`
- ส่ง heartbeat ไป `/voice-node/heartbeat`
- มี state machine พื้นฐาน
- เปิด INMP441 test ได้ผ่าน `menuconfig`
- อ่านค่า mic level เป็น `avg_abs`, `rms`, `peak` ผ่าน serial
- ยังไม่เปิด MAX98357A
- ยังไม่เปิด ESP-SR / WakeNet

Phase 1 Control Node ที่อยู่ใน `esp32/` ยังใช้ MicroPython เหมือนเดิม

---

## 1. สิ่งที่ต้องติดตั้ง

- ESP-IDF 5.x
- Git
- Python ที่ ESP-IDF ติดตั้งให้
- USB driver สำหรับ ESP32-S3 ถ้าจำเป็น

ถ้า installer สร้าง shortcut ให้ สามารถเปิด ESP-IDF PowerShell หรือ ESP-IDF CMD ได้ตามปกติ

ถ้าหา ESP-IDF Shell ไม่เจอ ให้ใช้สคริปต์ในโฟลเดอร์นี้แทนได้เลย:

```powershell
cd D:\smart-home-ai\firmware\voice_node_espidf

# เปิด PowerShell ใหม่ที่ export ESP-IDF environment ให้แล้ว
.\open_idf_shell.ps1

# หรือสั่งงานตรง ๆ โดยไม่ต้องเปิด shell ใหม่
.\idf_build.ps1
.\idf_list_ports.ps1
.\idf_flash_monitor.ps1 -Port COM3
```

ถ้าต้องการตั้งค่า Wi-Fi และ server แบบไม่เข้า `menuconfig`:

```powershell
.\idf_configure_local.ps1 -WifiSsid "ชื่อ Wi-Fi" -WifiPassword "รหัส Wi-Fi" -EnableMic
```

สคริปต์นี้จะหา IPv4 ของ notebook ให้อัตโนมัติ แล้วตั้ง `FastAPI server base URL` เป็น `http://<IPv4>:8000`

ถ้าต้องการเปิด MAX98357A beep test เพิ่ม:

```powershell
.\idf_configure_local.ps1 -WifiSsid "esp32" -WifiPassword "00000000" -ServerUrl "http://192.168.60.114:8000" -EnableMic -EnableSpeaker
```

---

## 2. ตั้งค่า project

```powershell
cd D:\smart-home-ai\firmware\voice_node_espidf
idf.py set-target esp32s3
idf.py menuconfig
```

ใน `menuconfig` ไปที่:

```text
AI Smart Home Voice Node
```

ตั้งค่า:

```text
Voice node device id      = voice-node-01
Wi-Fi SSID                = ชื่อ Wi-Fi หรือ hotspot
Wi-Fi password            = รหัส Wi-Fi
FastAPI server base URL   = http://<IPv4 ของ notebook>:8000
Heartbeat interval        = 15000
```

ถ้าจะทดสอบ INMP441 ให้เปิด:

```text
Enable INMP441 microphone RMS test = y
INMP441 WS/LRCLK GPIO              = 16
INMP441 SCK/BCLK GPIO              = 17
INMP441 SD/DIN GPIO                = 18
INMP441 sample rate                = 16000
Microphone stats log interval      = 1000
```

ห้ามใช้ `127.0.0.1` ในบอร์ด เพราะจะหมายถึงตัว ESP32 เอง ให้ใช้ IPv4 ของ notebook เช่น:

```text
http://192.168.1.50:8000
```

หา IPv4 บน Windows:

```powershell
ipconfig
```

---

## 3. เตรียม server

บน notebook ให้รัน FastAPI ด้วย host `0.0.0.0` เพื่อให้บอร์ดยิงเข้ามาได้:

```powershell
cd D:\smart-home-ai
.\.venv\Scripts\Activate.ps1
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

เช็ก endpoint:

```powershell
curl.exe http://127.0.0.1:8000/voice-node/config
```

ควรได้ JSON ที่มี `device_id`, `enabled`, `wake_word`, `audio_endpoint`

---

## 4. Build / Flash / Monitor

```powershell
cd D:\smart-home-ai\firmware\voice_node_espidf
idf.py build
idf.py -p COMx flash monitor
```

เปลี่ยน `COMx` เป็น port จริง เช่น `COM6`

ออกจาก monitor:

```text
Ctrl + ]
```

---

## 5. Serial log ที่ควรเห็น

ตัวอย่าง:

```text
I voice_node: Device id: voice-node-01
I voice_node: Server: http://192.168.1.50:8000
I voice_node: State -> WIFI_CONNECTING
I wifi_manager: Got IP: 192.168.1.80
I voice_node: State -> REGISTERING
I voice_http: Config: enabled=1 wake_word=Hi ESP record_seconds=4 sample_rate=16000 audio=wav reply=mp3
I voice_node: State -> WAKE_LISTENING
I voice_http: Heartbeat ok: WAKE_LISTENING
```

ถ้าเปิด mic test และต่อ INMP441 ถูกต้อง ควรเห็น log เพิ่ม:

```text
I mic_reader: INMP441 enabled: ws=16 sck=17 sd=18 sample_rate=16000
I voice_node: Mic level: samples=512 avg_abs=... rms=... peak=...
```

ตอนห้องเงียบ ค่า `avg_abs/rms/peak` ควรต่ำกว่า ตอนพูดใกล้ไมค์ควรเพิ่มชัดเจน ถ้าค่าไม่เปลี่ยนเลยให้เช็กสาย WS/SCK/SD และ L/R -> GND

### Button audio upload test

Firmware milestone นี้รองรับการกดปุ่ม BOOT เพื่อทดสอบอัดเสียงจาก INMP441 แล้วส่งไป server โดยตรง
โดยไม่ต้องรอ wake word:

```text
BOOT button / GPIO0 -> record 4 seconds -> POST /assistant/audio
```

ถ้าเปิด `-EnableSpeaker` หรือเปิด `Enable MAX98357A speaker beep test` ใน menuconfig
บอร์ดจะเล่น beep สั้น ๆ ก่อนเริ่มอัดเสียง เพื่อยืนยันว่าลำโพงพร้อมและช่วยให้ผู้ใช้รู้จังหวะเริ่มพูด

วิธีทดสอบ:

1. รัน server ด้วย `--host 0.0.0.0`
2. เปิด serial monitor หรือรัน `.\idf_flash_monitor.ps1 -Port COM10`
3. รอให้เห็น `State -> WAKE_LISTENING`
4. กดปุ่ม BOOT หนึ่งครั้ง แล้วพูดคำสั่งภาษาไทยใกล้ INMP441 ภายใน 4 วินาที
5. ควรเห็น log ประมาณนี้:

```text
I button_reader: Button audio upload trigger enabled: gpio=0 active_low=1
I voice_node: Button pressed: record and upload one voice command
I voice_node: State -> RECORDING_COMMAND
I mic_reader: Recorded WAV: seconds=4 bytes=128044
I voice_node: State -> UPLOADING_AUDIO
I voice_http: Audio upload ok: {...}
I voice_node: State -> WAKE_LISTENING
```

หมายเหตุ:

- อย่ากด BOOT ค้างตอน reset/เสียบสาย USB เพราะอาจเข้า download mode
- กดตอน firmware รันอยู่แล้วเท่านั้น
- ถ้า `heard_text` ว่าง ให้พูดให้ใกล้ไมค์ขึ้น หันช่องรับเสียงของ INMP441 เข้าหาปาก และลดเสียงรบกวนรอบข้าง

---

## 6. ต่อสาย MAX98357A สำหรับ beep test

```text
MAX98357A VIN  -> 5V หรือ 3.3V ตามโมดูล
MAX98357A GND  -> GND
MAX98357A LRC  -> GPIO9
MAX98357A BCLK -> GPIO10
MAX98357A DIN  -> GPIO11
Speaker +      -> SPK+
Speaker -      -> SPK-
```

ใช้ไฟให้เหมาะกับโมดูล MAX98357A และต้อง common GND กับ ESP32-S3

---

## 7. ทดสอบจากฝั่ง server

หลัง firmware รันแล้ว:

```powershell
curl.exe "http://127.0.0.1:8000/voice-node/status?device_id=voice-node-01"
```

คาดหวัง:

```json
{
  "device_id": "voice-node-01",
  "online": true,
  "enabled": true,
  "state": "WAKE_LISTENING"
}
```

---

## 8. ถ้าเชื่อมต่อไม่ได้

เช็กตามลำดับ:

1. Notebook และ ESP32 อยู่ Wi-Fi วงเดียวกัน
2. Server รันด้วย `--host 0.0.0.0`
3. `FastAPI server base URL` เป็น IPv4 ของ notebook ไม่ใช่ `127.0.0.1`
4. Windows Firewall ไม่บล็อก port 8000
5. ลองเปิดจากมือถือใน Wi-Fi วงเดียวกัน: `http://<IPv4>:8000/health`
6. SSID/password ใน `idf.py menuconfig` ถูกต้อง

---

## 9. ต่อสาย INMP441 สำหรับ Phase 2C

```text
INMP441 VDD -> 3.3V
INMP441 GND -> GND
INMP441 WS  -> GPIO16
INMP441 SCK -> GPIO17
INMP441 SD  -> GPIO18
INMP441 L/R -> GND
```

อย่าใช้ 5V กับ INMP441

---

## 10. Step ถัดไป

หลัง heartbeat และ mic level ผ่านแล้วค่อยไป Phase 2D/2E:

- อัด buffer 3-4 วินาทีและ upload WAV ไป `/assistant/audio` ผ่านปุ่ม BOOT ให้ STT อ่านได้ชัด
- เพิ่ม ESP-SR WakeNet
- เพิ่ม MAX98357A playback
