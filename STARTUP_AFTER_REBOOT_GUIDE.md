# Startup Guide After Reboot

## Recommended Quick Start (อัปเดตล่าสุด)

ตอนนี้วิธีที่แนะนำที่สุดหลังเปิดเครื่องใหม่คือใช้ script เดียว:

```powershell
cd D:\smart-home-ai
.\run_all.bat
```

หรือถ้าต้องการเรียก PowerShell โดยตรง:

```powershell
cd D:\smart-home-ai
powershell -NoProfile -ExecutionPolicy Bypass -File .\start_demo.ps1
```

script นี้จะช่วยทำงานสำคัญให้ครบ:

1. เช็คหรือเปิด Ollama ที่ `http://127.0.0.1:11434`
2. ใช้ path โมเดล `D:\Ollama_Models`
3. เช็คโมเดลจาก `OLLAMA_MODEL` ใน `.env`
4. ปิด FastAPI/uvicorn เก่าที่ค้างอยู่บน port 8000
5. เปิด server แบบไม่ใช้ `--reload` เพื่อให้เดโมนิ่งกว่า
6. รอ `/health`
7. สั่ง warmup โมเดลผ่าน `/health/llm/warmup`
8. เช็คสถานะรวมด้วย `check_demo_status.ps1`
9. เปิด Dashboard ที่ `http://127.0.0.1:8000/`

ถ้าต้องการเช็คสถานะอย่างเดียวโดยไม่เปิด/ปิดอะไร:

```powershell
cd D:\smart-home-ai
powershell -NoProfile -ExecutionPolicy Bypass -File .\check_demo_status.ps1
```

ถ้าต้องการปิด server เดโมหลังใช้งานเสร็จ:

```powershell
cd D:\smart-home-ai
powershell -NoProfile -ExecutionPolicy Bypass -File .\stop_demo.ps1
```

ถ้าต้องการปิดทั้ง server และ Ollama:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\stop_demo.ps1 -StopOllama
```

ถ้าต้องการเปิด server โดยไม่ปิด server เก่าก่อน:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start_demo.ps1 -NoServerRestart
```

หมายเหตุสำหรับเดโม: ไม่แนะนำให้ใช้ `uvicorn --reload` ตอนนำเสนอ เพราะอาจเกิด parent/child process ซ้อน ทำให้วัด latency ยากและบางครั้งเหมือนระบบหลับเอง

คู่มือนี้ใช้สำหรับกรณีปิดเครื่องแล้วเปิดใหม่ แล้วต้องการให้ระบบ `AI Smart Home Thai Assistant` กลับมาทำงานเหมือนเดิมแบบเป็นขั้นตอน

เอกสารนี้ตั้งใจเขียนให้ทำตามได้ทีละข้อ โดยไม่ต้องเดา

---

## 1. เป้าหมายหลังเปิดเครื่อง

เมื่อทำครบแล้ว ระบบควรอยู่ในสภาพนี้:

1. Ollama ทำงานอยู่ที่ `http://localhost:11434`
2. FastAPI ทำงานอยู่ที่ `http://127.0.0.1:8000`
3. Dashboard เปิดได้ที่ `http://127.0.0.1:8000/`
4. API docs เปิดได้ที่ `http://127.0.0.1:8000/docs`
5. ESP32 ส่ง heartbeat ได้
6. Dashboard แสดง `ESP32 online`
7. `/chat` ตอบได้
8. เสียง TTS ใช้งานได้

---

## 2. สิ่งที่ต้องมี

ก่อนเริ่ม ให้เช็กว่ามีสิ่งเหล่านี้:

1. เครื่อง Windows เปิดเรียบร้อย
2. โปรเจกต์อยู่ที่ `D:\smart-home-ai`
3. Ollama ติดตั้งแล้ว
4. โมเดล Ollama อยู่ใน `D:\Ollama_Models`
5. ESP32 ต่อไฟและพร้อมใช้งาน ถ้าจะทดสอบฮาร์ดแวร์
6. เครื่องคอมและ ESP32 อยู่ Wi-Fi วงเดียวกัน

---

## 3. Quick Start แบบสั้น

ถ้าต้องการเวอร์ชันสั้นมาก ให้ทำตามนี้:

1. เปิด PowerShell ที่ `D:\smart-home-ai`
2. รัน `.\start_ollama_clean.bat`
3. เปิด PowerShell ใหม่ แล้วรัน server:

```powershell
cd D:\smart-home-ai
.\.venv\Scripts\Activate.ps1
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

4. เปิด browser ที่:
   - `http://127.0.0.1:8000/`
   - `http://127.0.0.1:8000/docs`
5. ถ้า ESP32 ใช้งานอยู่ ให้รอ heartbeat 5-30 วินาที
6. ถ้า dashboard ยังขึ้น offline ให้ตรวจ `esp32/config.py` โดยเฉพาะ `SERVER_BASE_URL`

ถ้าต้องการแบบละเอียด ให้ดูหัวข้อถัดไป

---

## 4. ขั้นตอนแบบละเอียดทีละข้อ

### Step 1: เปิดโฟลเดอร์โปรเจกต์

เปิด PowerShell แล้วพิมพ์:

```powershell
cd D:\smart-home-ai
```

เช็กว่ามีไฟล์สำคัญ:

```powershell
dir
```

ควรเห็นไฟล์ประมาณนี้:

- `.env`
- `requirements.txt`
- `start_ollama_clean.bat`
- `server\`
- `esp32\`
- `webui\`

---

### Step 2: เริ่ม Ollama ให้ถูกวิธี

โปรเจกต์นี้ใช้ไฟล์:

- `start_ollama_clean.bat`

ไฟล์นี้จะ:

1. ปิด Ollama เดิม
2. ตั้ง `OLLAMA_MODELS=D:\Ollama_Models`
3. สั่ง `ollama serve`

ให้รัน:

```powershell
cd D:\smart-home-ai
.\start_ollama_clean.bat
```

ถ้าทำงานถูก จะมีหน้าต่างใหม่เปิดขึ้นและ Ollama เริ่มทำงาน

---

### Step 3: ตรวจว่า Ollama พร้อม

เปิด PowerShell อีกหน้าต่าง แล้วทดสอบ:

```powershell
curl.exe http://localhost:11434/api/tags
```

ถ้าปกติ จะได้ JSON กลับมา

ถ้าไม่ตอบ:

1. เช็กว่าหน้าต่าง `ollama serve` ยังเปิดอยู่ไหม
2. เช็กว่ามี process Ollama ค้างหรือไม่
3. รัน `.\start_ollama_clean.bat` ใหม่

---

### Step 4: เริ่ม FastAPI server

เปิด PowerShell อีกหน้าต่าง แล้วรัน:

```powershell
cd D:\smart-home-ai
.\.venv\Scripts\Activate.ps1
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

ถ้า `.venv` ใช้ไม่ได้ ให้ใช้ Python 3.11+ ที่ติดตั้งในเครื่องแทน:

```powershell
cd D:\smart-home-ai
py -3.11 -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```

หมายเหตุ:

- ตอนนี้ **ไม่แนะนำให้ใช้ `run_all.bat` เป็นตัวหลัก**
- เพราะไฟล์นี้อ้างถึง `warmup.py` แต่ใน repo ปัจจุบันไม่มีไฟล์นี้
- ถ้าจะใช้จริง ควรแก้สคริปต์นั้นก่อน

---

### Step 5: ตรวจ health ของ server

เมื่อ server ขึ้นแล้ว ให้ทดสอบ:

```powershell
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8000/ready
curl.exe http://127.0.0.1:8000/health/llm
```

สิ่งที่ควรได้:

1. `/health` ตอบได้
2. `/ready` ตอบได้
3. `/health/llm` ไม่ควร error

ถ้า `/health` ยังไม่ได้ แปลว่า server ยังไม่ขึ้นจริง

---

### Step 6: เปิดหน้าใช้งาน

เปิด browser ที่:

- Dashboard: `http://127.0.0.1:8000/`
- Docs: `http://127.0.0.1:8000/docs`

สิ่งที่ควรเห็น:

1. Dashboard เปิดได้
2. Chat Panel เปิดได้
3. Device Control Panel เปิดได้
4. Motion Panel เปิดได้
5. Voice / TTS Panel เปิดได้

---

### Step 7: เช็กไฟล์ config สำคัญของ ESP32

เปิดไฟล์:

- `D:\smart-home-ai\esp32\config.py`

เช็กค่าหลัก:

```python
DEVICE_ID = "esp32-01"
SERVER_BASE_URL = "http://192.168.136.114:8000"

DHT22_PIN = 4
RELAY_PIN = 5
PIR_PIN = 6
MOTION_ENABLED = True
```

จุดสำคัญที่สุดหลังเปิดเครื่องใหม่คือ:

### `SERVER_BASE_URL` อาจต้องเปลี่ยน

ถ้า IP ของคอมเปลี่ยนหลัง reboot หรือเปลี่ยน Wi-Fi / hotspot:

1. ESP32 จะยังยิงไป IP เก่า
2. heartbeat อาจไม่เข้า server ตัวใหม่
3. dashboard จะขึ้น offline

วิธีเช็ก IP เครื่องปัจจุบัน:

```powershell
ipconfig
```

หา IPv4 Address ของ network ที่ใช้งานอยู่ แล้วเอาไปแทนใน `SERVER_BASE_URL`

ตัวอย่าง:

```python
SERVER_BASE_URL = "http://192.168.1.100:8000"
```

แล้วอัปโหลด `esp32/config.py` ใหม่ลงบอร์ด

---

### Step 8: ให้ ESP32 ทำงาน

ถ้าบอร์ดยังไม่ได้รัน code:

1. เปิด Thonny
2. เชื่อมต่อ ESP32
3. เปิดโฟลเดอร์ `esp32/`
4. อัปโหลดไฟล์อย่างน้อย:
   - `config.py`
   - `wifi_manager.py`
   - `api_client.py`
   - `sensor_reader.py`
   - `motion_reader.py`
   - `main.py`
5. รัน `main.py`

---

### Step 9: เช็ก heartbeat จาก ESP32

ดูที่ serial/console ของ ESP32

ถ้าปกติ ควรเห็นข้อความแนวนี้:

```text
Heartbeat: {'status': 'ok'}
```

จากนั้นให้เช็กจากฝั่ง server:

```powershell
curl.exe "http://127.0.0.1:8000/esp32/status?device_id=esp32-01"
```

ควรได้ประมาณนี้:

```json
{
  "device_id": "esp32-01",
  "online": true,
  "last_seen_at": "...",
  "seconds_since_heartbeat": 0,
  "pending_command_count": 0,
  "latest_command": null
}
```

ถ้ายัง `online=false`:

1. เช็ก `SERVER_BASE_URL` ใน ESP32
2. เช็กว่าเครื่องคอมกับบอร์ดอยู่ Wi-Fi วงเดียวกัน
3. เช็กว่า firewall ไม่บล็อก port `8000`
4. เช็กว่า server ที่ `:8000` คือ instance เดียวกับที่ browser เปิดอยู่

---

### Step 10: เช็ก sensor / motion / relay

#### 10.1 เช็ก sensor

```powershell
curl.exe http://127.0.0.1:8000/dashboard/status
```

ดู field:

- `sensor.temperature`
- `sensor.humidity`

#### 10.2 เช็ก motion

ขยับตัวหน้าตัว PIR แล้วดู:

- Dashboard Motion Panel
- หรือถามใน chat:

```text
มีคนเดินผ่านไหม
```

#### 10.3 เช็ก relay

ผ่าน chat:

```text
เปิดไฟ
ปิดไฟ
```

หรือดูคิวคำสั่ง:

```powershell
curl.exe "http://127.0.0.1:8000/esp32/commands?device_id=esp32-01"
```

---

### Step 11: เช็ก chat, weather, news, navigation, traffic

ตัวอย่างที่ใช้ทดสอบเร็ว:

#### Chat / LLM

```powershell
curl.exe -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"สวัสดี\"}"
```

#### Sensor

```powershell
curl.exe -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"ห้องร้อนไหม\"}"
```

#### Motion

```powershell
curl.exe -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"มีคนอยู่ไหม\"}"
```

#### Weather

```powershell
curl.exe -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"วันนี้ยะลาอากาศยังไง\"}"
```

#### News

```powershell
curl.exe -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"วันนี้มีข่าวอะไรบ้าง\"}"
```

#### Navigation

```powershell
curl.exe -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"ไปสนามบินใช้เวลากี่นาที\"}"
```

#### Traffic

```powershell
curl.exe -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"ในยะลารถติดไหม\"}"
```

---

### Step 12: เช็ก TTS

ทดสอบแยก:

```powershell
curl.exe -X POST http://127.0.0.1:8000/voice/speak -H "Content-Type: application/json" -d "{\"text\":\"สวัสดี วันนี้พร้อมทำงานแล้ว\"}"
```

เช็กสถานะ:

```powershell
curl.exe http://127.0.0.1:8000/voice/status
```

ถ้าปกติ:

1. จะได้ `audio_url`
2. หน้า dashboard จะเล่นเสียงได้
3. `static/current_reply.mp3` จะถูกเขียนทับไฟล์เดิม

---

## 5. ลำดับการเปิดระบบที่แนะนำจริง

ถ้าต้องการลดปัญหา ให้เปิดตามลำดับนี้เสมอ:

1. เปิดคอม
2. ต่ออินเทอร์เน็ต / hotspot ให้เรียบร้อย
3. รัน `start_ollama_clean.bat`
4. รัน FastAPI server
5. เปิด dashboard
6. เช็กว่า `/health` และ `/ready` ผ่าน
7. เช็ก IP เครื่อง
8. เช็ก `esp32/config.py` ว่า `SERVER_BASE_URL` ยังชี้ IP ปัจจุบัน
9. ค่อยเปิด/รีเซ็ต ESP32
10. รอ heartbeat แล้วค่อยทดสอบ chat และอุปกรณ์

---

## 6. ปัญหาที่เจอบ่อยหลังเปิดเครื่องใหม่

### ปัญหา 1: Dashboard เปิดได้ แต่บอร์ด offline

สาเหตุที่พบบ่อย:

1. `SERVER_BASE_URL` ใน ESP32 ชี้ IP เก่า
2. ESP32 ยังไม่ได้รัน `main.py`
3. คอมกับบอร์ดอยู่คนละ network
4. server ไม่ได้เปิดที่ port `8000`

วิธีแก้:

1. เช็ก `ipconfig`
2. แก้ `esp32/config.py`
3. อัปโหลดไฟล์ใหม่
4. รัน `main.py`
5. เรียก `/esp32/status`

---

### ปัญหา 2: Ollama ไม่ตอบ

วิธีเช็ก:

```powershell
curl.exe http://localhost:11434/api/tags
```

วิธีแก้:

1. ปิด Ollama เดิม
2. รัน `start_ollama_clean.bat`
3. รอให้ `ollama serve` พร้อม

---

### ปัญหา 3: Chat ตอบ fallback เรื่องโมเดลช้า

วิธีเช็ก:

```powershell
curl.exe http://127.0.0.1:8000/health/llm
```

วิธีแก้:

1. เช็ก Ollama ก่อน
2. รอ warmup ให้เสร็จ
3. ลองถามสั้น ๆ ก่อน เช่น `สวัสดี`

---

### ปัญหา 4: TTS ไม่มีเสียง

วิธีเช็ก:

```powershell
curl.exe http://127.0.0.1:8000/voice/status
```

ดูค่า:

- `audio_ready`
- `file_size_bytes`
- `last_error`

---

### ปัญหา 5: ESP32 ขึ้น `Loop error: [Errno 113] ECONNABORTED`

ตอนนี้โค้ดมี retry และ reconnect แล้ว แต่ถ้ายังเจอ:

1. เช็กว่า Wi-Fi เสถียรไหม
2. เช็กว่า `SERVER_BASE_URL` ถูกไหม
3. เช็กว่า server ยังเปิดอยู่
4. กด reset ESP32 1 รอบ

ถ้ายังไม่หาย:

1. ปิด `main.py`
2. เปิดใหม่
3. ดู serial log ตั้งแต่ต้น

---

## 7. คำสั่งที่ใช้บ่อย

### เริ่ม Ollama

```powershell
cd D:\smart-home-ai
.\start_ollama_clean.bat
```

### เริ่ม FastAPI

```powershell
cd D:\smart-home-ai
.\.venv\Scripts\Activate.ps1
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

### เช็ก health

```powershell
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8000/ready
curl.exe http://127.0.0.1:8000/health/llm
```

### เช็กสถานะ ESP32

```powershell
curl.exe "http://127.0.0.1:8000/esp32/status?device_id=esp32-01"
```

### เปิด dashboard

```text
http://127.0.0.1:8000/
```

### เปิด docs

```text
http://127.0.0.1:8000/docs
```

---

## 8. Checklist ก่อนเริ่ม present

ให้เช็กทีละข้อ:

- [ ] Ollama เปิดอยู่
- [ ] FastAPI เปิดอยู่
- [ ] `/health` ผ่าน
- [ ] `/health/llm` ผ่าน
- [ ] Dashboard เปิดได้
- [ ] `/esp32/status` เป็น `online=true`
- [ ] sensor ขึ้นค่าจริง
- [ ] motion panel ใช้งานได้
- [ ] relay สั่งเปิด/ปิดได้
- [ ] weather ตอบได้
- [ ] news ตอบได้
- [ ] navigation ตอบได้
- [ ] traffic ตอบได้
- [ ] TTS มีเสียง

---

## 9. Checklist หลังเปลี่ยน Wi-Fi หรือ hotspot

ถ้าเปลี่ยน network ให้ทำทันที:

1. รัน `ipconfig`
2. จด IPv4 ใหม่ของคอม
3. แก้ `esp32/config.py` ตรง `SERVER_BASE_URL`
4. อัปโหลด `config.py` ลง ESP32
5. reset บอร์ด
6. เช็ก `/esp32/status`

---

## 10. สรุปสั้นที่สุด

ถ้ารีบมาก ให้จำแค่นี้:

1. เปิด `start_ollama_clean.bat`
2. เปิด `uvicorn server.app:app --host 0.0.0.0 --port 8000`
3. เปิด `http://127.0.0.1:8000/`
4. เช็ก `/esp32/status`
5. ถ้าบอร์ด offline ให้เช็ก `SERVER_BASE_URL` ใน `esp32/config.py`
