# AI Smart Home Thai Assistant

คู่มือนี้สำหรับ clone โปรเจ็กต์ไปเครื่องใหม่ แล้วติดตั้งตั้งแต่ต้นจนรันระบบได้จริงบน Windows

โปรเจ็กต์นี้คือระบบผู้ช่วยบ้านอัจฉริยะภาษาไทยที่ใช้ FastAPI, Web UI, Ollama Local LLM, Thai TTS/STT, ESP32-S3, DHT22, relay และ PIR motion sensor โดยออกแบบให้รันในเครื่อง local และใช้ external APIs เฉพาะข้อมูลสด เช่น อากาศ ข่าว เส้นทาง และจราจร

> สำคัญ: ไฟล์ `.env` ถูก ignore และจะไม่ถูก clone ไปด้วย เพราะมี API keys/secrets ต้องสร้างใหม่บนเครื่องใหม่เอง

---

## 1. สิ่งที่ต้องติดตั้งบนเครื่องใหม่

### 1.1 Required

- Windows 10/11
- Git
- Python 3.11 ขึ้นไป
- Ollama
- Google Chrome หรือ Microsoft Edge สำหรับ Web UI และ browser microphone

### 1.2 Recommended

- VS Code
- Thonny สำหรับ upload MicroPython ไป ESP32
- MicroPython firmware สำหรับ ESP32-S3
- Internet สำหรับ external APIs และ Edge TTS

### 1.3 Hardware ที่โปรเจ็กต์รองรับตอนนี้

- ESP32-S3
- DHT22
- 1-channel relay
- HC-SR501 PIR motion sensor
- INMP441 มี starter foundation เท่านั้น ยังไม่ใช่ voice input หลัก

---

## 2. Clone โปรเจ็กต์

เปิด PowerShell แล้วรัน:

```powershell
cd C:\
git clone <YOUR_REPOSITORY_URL> smart-home-ai
cd C:\smart-home-ai
```

ถ้าต้องการวางไว้ drive อื่นก็ได้ เช่น:

```powershell
cd D:\
git clone <YOUR_REPOSITORY_URL> smart-home-ai
cd D:\smart-home-ai
```

หลัง clone แล้วควรเห็นไฟล์/โฟลเดอร์ประมาณนี้:

```text
server/
webui/
esp32/
prompts/
docs/
requirements.txt
start_demo.ps1
run_all.bat
check_demo_status.ps1
```

---

## 3. สร้าง Python virtual environment

แนะนำให้ใช้ `.venv` ในโปรเจ็กต์:

```powershell
cd C:\smart-home-ai
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

ถ้า PowerShell ไม่ยอม activate venv ให้รัน:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

ตรวจว่า Python ใช้งานได้:

```powershell
python --version
python -c "import server.app; print('APP_IMPORT_OK')"
```

ควรได้:

```text
APP_IMPORT_OK
```

---

## 4. ติดตั้งและตั้งค่า Ollama แบบปกติ

เครื่องใหม่นี้ให้ใช้ Ollama แบบปกติ ไม่ต้องใช้ `D:\Ollama_Models`

1. ติดตั้ง Ollama จาก https://ollama.com
2. ปิดแล้วเปิด PowerShell ใหม่
3. ตรวจว่า Ollama ใช้งานได้:

```powershell
ollama --version
```

4. เริ่ม Ollama ตามปกติ:

```powershell
ollama serve
```

หรือเปิด Ollama จาก Start Menu ก็ได้

5. ติดตั้ง model ที่ต้องการใช้

ถ้าจะใช้ model ที่โปรเจ็กต์ปรับไว้ล่าสุด:

```powershell
ollama pull gemma4:e2b
```

ถ้าเครื่องหรือ Ollama ไม่มี tag นี้ ให้ใช้ model ที่ติดตั้งได้จริง แล้วนำชื่อ model ไปใส่ใน `.env` ที่ `OLLAMA_MODEL`

ตัวเลือกอื่น:

```powershell
ollama pull scb10x/llama3.1-typhoon2-8b-instruct:latest
```

ตรวจ model ที่มี:

```powershell
ollama list
```

ทดสอบ Ollama API:

```powershell
curl.exe http://127.0.0.1:11434/api/tags
```

### ห้ามพลาดเรื่อง path ของ Ollama

ในเครื่องเดิมเคยใช้ `D:\Ollama_Models` แต่เครื่องใหม่ให้ใช้ path ปกติของ Ollama

ดังนั้น:

- ไม่ต้องตั้ง `OLLAMA_MODELS=D:\Ollama_Models`
- ไม่ควรใช้ `start_ollama_clean.bat` บนเครื่องใหม่ ถ้ายังไม่ได้แก้ path ข้างใน
- วิธีที่ปลอดภัยที่สุดคือเปิด Ollama เองก่อน แล้วรัน server ด้วย `-NoOllamaStart`

ตัวอย่าง:

```powershell
ollama serve
```

เปิด PowerShell อีกหน้าต่าง:

```powershell
cd C:\smart-home-ai
.\.venv\Scripts\Activate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\start_demo.ps1 -NoOllamaStart
```

---

## 5. สร้างไฟล์ .env

สร้างไฟล์ `.env` ที่ root ของโปรเจ็กต์:

```powershell
cd C:\smart-home-ai
notepad .env
```

ใส่ค่าตัวอย่างนี้ แล้วแทนค่า secret จริงของคุณเอง:

```env
# App
APP_ENV=development
APP_DEBUG=false
DEBUG_LOGS=false
DEMO_MODE=true

# Ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_TIMEOUT_SECONDS=120
OLLAMA_KEEP_ALIVE=30m
OLLAMA_WARMUP_TIMEOUT_SECONDS=75
LLM_WARMUP_ON_START=true
LLM_KEEP_AWAKE_IN_DEMO=true
LLM_KEEP_AWAKE_INTERVAL_SECONDS=240
LLM_GENERAL_MAX_TOKENS=32
LLM_REASONING_MAX_TOKENS=48
LLM_THINKING_MAX_TOKENS=384
LLM_NUM_CTX=1024
LLM_TEMPERATURE=0.2

# ถ้าใช้ Ollama path ปกติ ให้ปล่อยว่างหรือไม่ต้องใส่บรรทัดนี้
OLLAMA_MODELS=

# ESP32
DEFAULT_ESP32_DEVICE_ID=esp32-01
ESP32_OFFLINE_TIMEOUT_SECONDS=60
DEFAULT_RELAY_GPIO_PIN=5
DEFAULT_RELAY_ACTIVE_HIGH=true
DEFAULT_DHT22_GPIO_PIN=4
DEFAULT_PIR_GPIO_PIN=6
DEVICE_REGISTRY_PATH=data/device_registry.json
SENSOR_FRESHNESS_SECONDS=300

# Weather
OPENWEATHER_API_KEY=ใส่_api_key_ของคุณ
DEFAULT_WEATHER_LOCATION=Yala,TH
WEATHER_TIMEOUT_SECONDS=5
WEATHER_CACHE_TTL_SECONDS=600

# News
CURRENTS_API_KEY=ใส่_api_key_ของคุณ
NEWS_PROVIDER=currents
NEWS_DEFAULT_LANGUAGE=th
NEWS_DEFAULT_COUNTRY=TH
NEWS_CACHE_TTL_SECONDS=600
NEWS_TIMEOUT_SECONDS=5
NEWS_MAX_ITEMS=5

# Navigation / Traffic
NAV_PROVIDER=openrouteservice
OPENROUTESERVICE_API_KEY=ใส่_api_key_ของคุณ
NAV_DEFAULT_ORIGIN=Yala
NAV_TIMEOUT_SECONDS=5
NAV_CACHE_TTL_SECONDS=600
NAV_DEFAULT_LANGUAGE=th

TRAFFIC_PROVIDER=tomtom
TOMTOM_API_KEY=ใส่_api_key_ของคุณ
TRAFFIC_TIMEOUT_SECONDS=5
TRAFFIC_CACHE_TTL_SECONDS=300
TRAFFIC_DEFAULT_LOCATION=Yala
TRAFFIC_FLOW_ZOOM=10

# LINE Messaging
LINE_ENABLED=false
LINE_CHANNEL_ID=
LINE_CHANNEL_SECRET=
LINE_CHANNEL_ACCESS_TOKEN=
LINE_TARGET_ID=
LINE_TIMEOUT_SECONDS=5

# TTS
TTS_ENABLED=true
DEMO_VOICE_MODE=true
TTS_PROVIDER=edge_tts
TTS_OVERWRITE_OUTPUT=true
TTS_OUTPUT_FILE=current_reply.mp3
TTS_DEFAULT_VOICE=th-TH-PremwadeeNeural
TTS_OUTPUT_DIR=static

# STT
STT_PROVIDER=faster_whisper
STT_MODEL=small
STT_LANGUAGE=th
STT_TIMEOUT_SECONDS=30
STT_WARMUP_ON_START=true

# UI
MAX_CHAT_HISTORY_ITEMS=50
```

หมายเหตุ:

- อย่า commit `.env`
- ถ้า external API key ยังไม่มี ระบบยังรันได้ แต่ weather/news/navigation/traffic จะ fallback
- ถ้า LINE ยังไม่ใช้ ให้ `LINE_ENABLED=false`

---

## 6. รันระบบแบบแนะนำบนเครื่องใหม่

### Terminal 1: เปิด Ollama

```powershell
ollama serve
```

ถ้า Ollama เปิดอยู่แล้วจาก app ให้ข้ามได้

### Terminal 2: เปิด backend + dashboard

```powershell
cd C:\smart-home-ai
.\.venv\Scripts\Activate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\start_demo.ps1 -NoOllamaStart
```

หรือรัน FastAPI เองแบบตรง ๆ:

```powershell
cd C:\smart-home-ai
.\.venv\Scripts\Activate.ps1
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

ใช้ `--host 0.0.0.0` เพื่อให้ ESP32 ในวง Wi-Fi เดียวกันยิงเข้า server ได้

เปิดหน้าใช้งาน:

```text
Dashboard: http://127.0.0.1:8000/
API Docs:  http://127.0.0.1:8000/docs
```

---

## 7. ตรวจระบบหลังรัน

เปิด PowerShell อีกหน้าต่าง แล้วรัน:

```powershell
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8000/ready
curl.exe http://127.0.0.1:8000/health/llm
curl.exe http://127.0.0.1:8000/dashboard/status
curl.exe http://127.0.0.1:8000/voice/status
```

หรือใช้ script:

```powershell
cd C:\smart-home-ai
powershell -NoProfile -ExecutionPolicy Bypass -File .\check_demo_status.ps1
```

ถ้า LLM ยังไม่ warm ให้กดปุ่ม `ปลุก AI` ใน Dashboard หรือยิง:

```powershell
curl.exe -X POST http://127.0.0.1:8000/health/llm/warmup
```

---

## 8. ทดสอบ Chat

```powershell
curl.exe -X POST http://127.0.0.1:8000/chat `
  -H "Content-Type: application/json" `
  -d "{\"message\":\"สวัสดี\"}"
```

ทดสอบ intent หลัก:

```powershell
curl.exe -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"ห้องร้อนไหม\"}"
curl.exe -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"เปิดไฟ\"}"
curl.exe -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"วันนี้ยะลาอากาศยังไง\"}"
curl.exe -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"วันนี้มีข่าวอะไรบ้าง\"}"
curl.exe -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"ไปสนามบินใช้เวลากี่นาที\"}"
curl.exe -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"ในกรุงเทพรถติดไหม\"}"
curl.exe -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"ตอนนี้เชื่อมต่อกับระบบ IoT ไหม\"}"
```

---

## 9. ทดสอบ TTS

```powershell
curl.exe -X POST http://127.0.0.1:8000/voice/speak `
  -H "Content-Type: application/json" `
  -d "{\"text\":\"สวัสดี วันนี้ระบบพร้อมใช้งานแล้ว\"}"
```

เช็กสถานะ:

```powershell
curl.exe http://127.0.0.1:8000/voice/status
```

ใน demo mode ระบบจะเขียนทับไฟล์:

```text
static/current_reply.mp3
```

เพื่อไม่ให้ไฟล์เสียงสะสมเยอะ

---

## 10. ทดสอบ Browser Voice / Wake Word

เปิด Dashboard:

```text
http://127.0.0.1:8000/
```

ใช้ Chrome หรือ Edge

### Push-to-Talk

1. เลือก `Push-to-Talk Mode`
2. กด `Start talking`
3. พูดคำถาม
4. ระบบจะส่งเข้า `/chat` และเล่นเสียงตอบกลับ

### Wake Word Mode

1. เลือก `Wake Word Mode`
2. อนุญาต microphone
3. พูดว่า `น้องฟ้า`
4. หลังระบบ active แล้ว คุยต่อได้โดยไม่ต้องเรียกชื่อทุกครั้ง
5. ถ้าพูด `ขอบคุณ`, `พอแล้ว`, `เลิกคุย` ระบบจะกลับไปรอฟัง wake word
6. ถ้าต้องการปิดไมค์จริง ๆ ให้กด `Stop`

ข้อจำกัด:

- Browser SpeechRecognition รองรับดีที่สุดใน Chrome/Edge
- บน localhost ใช้ microphone ได้
- ถ้าใช้ IP LAN แล้ว browser บางตัวบล็อก microphone ให้ใช้ Chrome/Edge หรือปรับ permission

---

## 11. ตั้งค่า ESP32 บนเครื่องใหม่

แก้ไฟล์:

```text
esp32/config.py
```

ค่าที่ต้องแก้แน่นอน:

```python
WIFI_SSID = "ชื่อ Wi-Fi หรือ hotspot"
WIFI_PASSWORD = "รหัส Wi-Fi"
SERVER_BASE_URL = "http://<IPv4 ของคอมเครื่องใหม่>:8000"
```

หา IPv4 ของคอม:

```powershell
ipconfig
```

ตัวอย่าง:

```python
SERVER_BASE_URL = "http://192.168.1.50:8000"
```

ค่า pin ปัจจุบัน:

```python
DHT22_PIN = 4
RELAY_PIN = 5
PIR_PIN = 6

MOTION_ENABLED = True
MIC_ENABLED = False
```

อัปโหลดไฟล์ใน `esp32/` ไปบอร์ดด้วย Thonny:

```text
config.py
wifi_manager.py
api_client.py
sensor_reader.py
motion_reader.py
mic_reader.py
main.py
```

จากนั้นรัน `main.py`

---

## 12. Wiring ปัจจุบัน

### DHT22

```text
VCC  -> 3.3V หรือ 5V ตามโมดูล
GND  -> GND
DATA -> GPIO4
```

### Relay 1-channel

```text
VCC -> 5V
GND -> GND
IN  -> GPIO5
```

### PIR HC-SR501

```text
VCC -> 5V
OUT -> GPIO6
GND -> GND
```

### INMP441 foundation

ยังไม่ใช่ input หลักของระบบตอนนี้ แต่เตรียมไว้:

```text
WS  -> GPIO16
SCK -> GPIO17
SD  -> GPIO18
VDD -> 3.3V
GND -> GND
L/R -> GND
```

---

## 13. ตรวจ ESP32 จากฝั่ง server

หลังบอร์ดรัน `main.py` ควรเห็นใน Thonny:

```text
Heartbeat: {'status': 'ok'}
Capabilities: {'status': 'ok'}
```

เช็กจาก server:

```powershell
curl.exe "http://127.0.0.1:8000/esp32/status?device_id=esp32-01"
curl.exe "http://127.0.0.1:8000/esp32/capabilities?device_id=esp32-01"
```

ถ้า Dashboard ยังขึ้น offline:

1. ตรวจ `SERVER_BASE_URL` ใน `esp32/config.py`
2. ตรวจว่า server รันด้วย `--host 0.0.0.0`
3. ตรวจว่า ESP32 กับคอมอยู่ Wi-Fi วงเดียวกัน
4. ตรวจ Windows Firewall ว่าไม่บล็อก port 8000
5. Reset ESP32 แล้วดู log ใหม่

---

## 14. Device Registry และ GPIO

Device Registry อยู่ใน:

```text
data/device_registry.json
```

ไฟล์นี้ถูก ignore และจะถูกสร้างเองตอนรันครั้งแรก

ค่า default:

- relay_1 ใช้ GPIO5
- dht22_1 ใช้ GPIO4
- pir_1 ใช้ GPIO6

ใน Dashboard panel `Device Registry`:

- แก้ชื่ออุปกรณ์ได้
- แก้ห้องได้
- แก้ aliases ได้ เช่น `ไฟโต๊ะ, หลอดไฟ, ไฟ`
- เพิ่ม virtual device ได้
- เพิ่ม relay จริงได้เฉพาะเมื่อ ESP32 online และส่ง capabilities แล้ว
- ระบบจะกัน GPIO ซ้ำหรือ GPIO ที่ถูก reserved ไว้

ถ้าจะให้คำสั่ง `เปิดไฟโต๊ะ` ใช้งานกับ relay ตัวเดิม ให้แก้ alias ของ `relay_1` แทนการเพิ่ม relay ใหม่บน GPIO5

---

## 15. External APIs ที่ต้องมีถ้าต้องการข้อมูลสด

ระบบยังรันได้ถ้าไม่มี API key แต่ feature จะ fallback

| Feature | Env key |
| --- | --- |
| Weather | `OPENWEATHER_API_KEY` |
| News | `CURRENTS_API_KEY` |
| Navigation | `OPENROUTESERVICE_API_KEY` |
| Traffic | `TOMTOM_API_KEY` |
| LINE message | `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_TARGET_ID` |

หลังแก้ `.env` ให้ restart server ทุกครั้ง

---

## 16. คำสั่งรันประจำวันที่แนะนำ

### เปิดระบบ

Terminal 1:

```powershell
ollama serve
```

Terminal 2:

```powershell
cd C:\smart-home-ai
.\.venv\Scripts\Activate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\start_demo.ps1 -NoOllamaStart
```

### ปิดระบบ

```powershell
cd C:\smart-home-ai
powershell -NoProfile -ExecutionPolicy Bypass -File .\stop_demo.ps1
```

ถ้าจะปิด Ollama ด้วย:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\stop_demo.ps1 -StopOllama
```

---

## 17. ปัญหาที่พบบ่อย

### Port 8000 ใช้ไม่ได้หรือขึ้น WinError 10013

เช็ก process:

```powershell
netstat -ano | findstr :8000
```

ปิด process:

```powershell
Stop-Process -Id <PID> -Force
```

หรือเปลี่ยน port:

```powershell
uvicorn server.app:app --host 0.0.0.0 --port 8001
```

### `/chat` ตอบ fallback ว่าระบบช้า

เช็ก:

```powershell
curl.exe http://127.0.0.1:11434/api/tags
curl.exe http://127.0.0.1:8000/health/llm
```

สาเหตุหลัก:

- Ollama ยังไม่รัน
- `OLLAMA_MODEL` ใน `.env` ไม่ตรงกับ `ollama list`
- model ยังไม่ถูก pull
- model cold start ยังไม่ warm

แก้:

```powershell
ollama list
ollama pull <model-name>
curl.exe -X POST http://127.0.0.1:8000/health/llm/warmup
```

### Weather/news/traffic ตอบ fallback

เช็ก API key ใน `.env` และ restart server

### TTS ไม่มีเสียง

เช็ก:

```powershell
curl.exe http://127.0.0.1:8000/voice/status
```

Edge TTS ต้องใช้อินเทอร์เน็ต ถ้าเน็ตหลุดอาจสร้างเสียงไม่สำเร็จ

### ESP32 offline

เช็ก:

- `SERVER_BASE_URL`
- IP เครื่องใหม่
- Wi-Fi วงเดียวกัน
- server ใช้ `--host 0.0.0.0`
- Firewall

---

## 18. Checklist หลัง clone เครื่องใหม่

- [ ] Clone repo แล้ว
- [ ] สร้าง `.venv`
- [ ] `pip install -r requirements.txt`
- [ ] ติดตั้ง Ollama แล้ว
- [ ] Pull model แล้ว
- [ ] สร้าง `.env`
- [ ] `OLLAMA_MODEL` ตรงกับ `ollama list`
- [ ] Ollama ตอบ `http://127.0.0.1:11434/api/tags`
- [ ] FastAPI ตอบ `/health`
- [ ] Dashboard เปิดได้
- [ ] กด `ปลุก AI` ผ่าน
- [ ] Chat ตอบได้
- [ ] TTS มีเสียง
- [ ] แก้ `esp32/config.py` เป็น IP เครื่องใหม่
- [ ] ESP32 heartbeat เข้า
- [ ] Sensor แสดงค่า
- [ ] Relay สั่งได้
- [ ] PIR แสดง motion ได้

---

## 19. หมายเหตุสำหรับเครื่องที่มี GPU

ถ้าในอนาคตย้ายไป notebook ที่มี GPU เช่น GTX 1050 และ RAM 16GB:

- เริ่มจากรัน Ollama ปกติก่อน
- เลือก model ที่ตอบเร็วและคุณภาพพอ เช่น model 2B/4B ที่ทดสอบแล้วดี
- อย่ารันหลาย model พร้อมกันถ้าไม่จำเป็น เพราะกิน RAM/VRAM
- ใช้ `ollama ps` ดู model ที่กำลัง loaded
- ถ้าเครื่องเริ่มช้า ให้ลด context/token ใน `.env`

คำสั่งดู model ที่กำลังโหลด:

```powershell
ollama ps
```

---

## 20. สรุปสั้นที่สุด

```powershell
git clone <YOUR_REPOSITORY_URL> smart-home-ai
cd smart-home-ai
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
notepad .env
ollama pull gemma4:e2b
ollama serve
```

เปิด PowerShell อีกหน้าต่าง:

```powershell
cd C:\smart-home-ai
.\.venv\Scripts\Activate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\start_demo.ps1 -NoOllamaStart
```

เปิด:

```text
http://127.0.0.1:8000/
```

