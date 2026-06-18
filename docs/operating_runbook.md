# Operating Runbook

เอกสารนี้ใช้สำหรับ 3 สถานการณ์หลัก:

- เปิดคอมใหม่แล้วต้องรันระบบเดโมให้กลับมาทำงาน
- ใช้ PWA บนมือถือผ่าน Vercel + Cloudflare Quick Tunnel
- clone โปรเจกต์ไปเครื่องเพื่อนหรือเครื่องใหม่แล้วตั้งค่าตั้งแต่ศูนย์

## ภาพรวมการรัน

ระบบแบ่งเป็น 3 ชั้น:

- FastAPI backend บน notebook: รัน AI, device command queue, STT/TTS, dashboard และ API
- Vercel PWA frontend: หน้าแอปมือถือที่ติดตั้งบน Android/iOS ได้
- Cloudflare Quick Tunnel: URL ชั่วคราวแบบ HTTPS ให้ PWA บนมือถือเรียก backend ใน notebook ได้

บอร์ด ESP32/Voice Node ไม่ได้คุยกับ Vercel โดยตรง แต่คุยกับ FastAPI backend เหมือนเดิม

## เปิดคอมใหม่แล้วรันเดโม

เปิด PowerShell ที่ root ของโปรเจกต์:

```powershell
cd D:\smart-home-ai
```

ดึงโค้ดล่าสุดก่อน ถ้าจะใช้เวอร์ชันล่าสุดจาก GitHub:

```powershell
git pull
```

เริ่ม backend, Ollama และ warmup:

```powershell
.\start_demo.ps1
```

ถ้าต้องการใช้ PWA บนมือถือผ่าน Vercel ให้เปิด tunnel:

```powershell
.\start_pwa_tunnel.ps1
```

สคริปต์จะแสดงค่า 2 บรรทัดสำคัญ:

```text
Backend API: https://xxxx.trycloudflare.com
PWA URL:     https://smart-home-ai-lyart.vercel.app/app?apiBase=https://xxxx.trycloudflare.com
```

บนมือถือให้เปิด `PWA URL` หนึ่งครั้ง หรือเข้าแอปที่ติดตั้งไว้แล้วไปที่ Settings -> Backend API แล้วใส่ค่า `Backend API`

ตรวจสถานะหลังรัน:

```powershell
.\check_demo_status.ps1
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8000/voice/status
```

SQLite log จะถูกสร้างอัตโนมัติที่:

```text
data/smart_home.sqlite3
```

Log นี้เก็บข้อมูลของทั้ง 2 บอร์ด:

- Control Node `esp32-01`: heartbeat, DHT22, PIR motion, relay command/result
- Voice Node `voice-node-01`: heartbeat/state, audio/STT result, playback result

ไฟล์นี้เป็นข้อมูล runtime ของเครื่องนั้น ๆ ไม่ต้อง commit ขึ้น Git

## หยุดระบบ

หยุด Cloudflare tunnel:

```powershell
.\stop_pwa_tunnel.ps1
```

หยุด FastAPI:

```powershell
.\stop_demo.ps1
```

ถ้าต้องการหยุด Ollama ด้วย:

```powershell
.\stop_demo.ps1 -StopOllama
```

## สิ่งที่ต้องจำเกี่ยวกับ Cloudflare Quick Tunnel

- URL `https://xxxx.trycloudflare.com` จะเปลี่ยนทุกครั้งที่เริ่ม tunnel ใหม่
- ถ้า URL เปลี่ยน ต้องอัปเดต Backend API ใน PWA ใหม่
- ถ้า PWA ติดต่อ backend ไม่สำเร็จ ให้เช็กว่า `.\start_demo.ps1` ยังรันอยู่ และ tunnel ยังเปิดอยู่
- ถ้าเปิด PWA จาก Vercel ต้องใช้ HTTPS tunnel เพราะ browser/PWA ต้องใช้ HTTPS เพื่อขอไมค์

## Clone เครื่องเพื่อนหรือเครื่องใหม่

ติดตั้งโปรแกรมพื้นฐาน:

- Git
- Python 3.11
- Ollama
- Google Chrome หรือ Microsoft Edge
- cloudflared สำหรับ PWA tunnel ถ้าจะใช้มือถือผ่าน Vercel

clone repo:

```powershell
cd D:\
git clone https://github.com/Ming0807/smart-home-ai.git
cd D:\smart-home-ai
```

สร้าง virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

ถ้า PowerShell ไม่ยอม activate:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

สร้าง `.env` จาก template:

```powershell
Copy-Item .env.example .env
notepad .env
```

อย่างน้อยให้ตรวจค่าเหล่านี้:

```env
OLLAMA_MODEL=gemma4:e2b
DEFAULT_ESP32_DEVICE_ID=esp32-01
VOICE_NODE_DEFAULT_ID=voice-node-01
SQLITE_LOG_ENABLED=true
SQLITE_LOG_PATH=data/smart_home.sqlite3
OPENWEATHER_API_KEY=
CURRENTS_API_KEY=
OPENROUTESERVICE_API_KEY=
TOMTOM_API_KEY=
LINE_ENABLED=false
```

ถ้ายังไม่มี API key ระบบยังรันได้ แต่ฟีเจอร์ weather/news/navigation/traffic อาจ fallback หรือไม่ครบ

ติดตั้ง/ดึงโมเดล Ollama:

```powershell
ollama serve
ollama pull gemma4:e2b
ollama list
```

เปิดอีก PowerShell แล้วทดสอบ backend:

```powershell
cd D:\smart-home-ai
.\start_demo.ps1
```

เปิด dashboard:

```text
http://127.0.0.1:8000/
```

## ตั้งค่า cloudflared บนเครื่องใหม่

วิธีง่าย:

1. ดาวน์โหลด `cloudflared-windows-amd64.exe`
2. สร้างโฟลเดอร์ `tools` ใน repo ถ้ายังไม่มี
3. เปลี่ยนชื่อไฟล์เป็น `cloudflared.exe`
4. วางไว้ที่:

```text
D:\smart-home-ai\tools\cloudflared.exe
```

ทดสอบ:

```powershell
.\tools\cloudflared.exe --version
```

จากนั้นเปิด tunnel:

```powershell
.\start_pwa_tunnel.ps1
```

## อัปเดตหลัง git pull

หลังดึงโค้ดใหม่:

```powershell
git pull
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

ถ้ามี PWA cache version ใหม่ ให้ปิด PWA จาก recent apps แล้วเปิดใหม่

ถ้า backend ยังทำงานแปลกหลังอัปเดต ให้ restart:

```powershell
.\stop_demo.ps1
.\start_demo.ps1
.\stop_pwa_tunnel.ps1
.\start_pwa_tunnel.ps1
```

## Checklist ก่อนพรีเซ็นต์

- `.\check_demo_status.ps1` ผ่านรายการหลัก
- Dashboard เปิดได้ที่ `http://127.0.0.1:8000/`
- PWA เปิดได้ และ Settings -> Backend API เป็น Cloudflare URL ล่าสุด
- กดไมค์ใน PWA แล้ว browser ขออนุญาตไมค์
- `/voice/status` มี `tts_enabled=true`
- Ollama model ตรงกับ `OLLAMA_MODEL`
- ถ้าใช้บอร์ดจริง ให้เช็กว่า control board และ voice node ชี้ backend เครื่องเดียวกัน
- SQLite log มีข้อมูลล่าสุด:

```powershell
curl.exe http://127.0.0.1:8000/activity/recent
```

## เช็กระบบ 2 บอร์ดบนเครื่องใหม่

โปรเจกต์นี้มี 2 บอร์ดหลัก และทั้งคู่ต้องคุยกับ FastAPI backend ตัวเดียวกัน:

| บอร์ด | Device ID | หน้าที่ | เช็กสถานะ |
| --- | --- | --- | --- |
| Control Node | `esp32-01` | DHT22, PIR motion, relay, command polling | `curl.exe http://127.0.0.1:8000/dashboard/status` |
| Voice Node | `voice-node-01` | Wake word, mic, STT/TTS, speaker playback | `curl.exe "http://127.0.0.1:8000/voice-node/status?device_id=voice-node-01"` |

ถ้าย้ายไปเครื่องเพื่อน:

1. หา IPv4 ของเครื่องเพื่อนด้วย `ipconfig`
2. Control Node: แก้ `esp32/config.py` ให้ `SERVER_BASE_URL="http://<IPv4 เครื่องเพื่อน>:8000"` แล้วอัปโหลดไฟล์ใน `esp32/` ลงบอร์ด
3. Voice Node: ตั้งค่า firmware ให้ `CONFIG_VOICE_NODE_SERVER_BASE_URL="http://<IPv4 เครื่องเพื่อน>:8000"` แล้ว build/flash บอร์ด voice node
4. เปิด backend ด้วย `.\start_demo.ps1`
5. เช็กว่า `/dashboard/status`, `/voice-node/status`, `/voice-node/audio/report`, `/activity/recent` ตอบได้

หมายเหตุ: Vercel/PWA ไม่ต้อง deploy ใหม่เวลาเปลี่ยนเครื่อง แค่เปิด tunnel ใหม่แล้วใส่ Backend API URL ใหม่ใน PWA

## ทดสอบ PIR Motion และ SQLite Log แบบไม่ต้องเสียบบอร์ด

ใช้ curl จำลอง event จาก PIR:

```powershell
$now = (Get-Date).ToUniversalTime().ToString("o")
curl.exe -X POST http://127.0.0.1:8000/esp32/motion `
  -H "Content-Type: application/json" `
  -d "{\"device_id\":\"esp32-01\",\"motion\":true,\"timestamp\":\"$now\"}"
```

ตรวจ dashboard status:

```powershell
curl.exe http://127.0.0.1:8000/dashboard/status
```

ตรวจ activity log:

```powershell
curl.exe http://127.0.0.1:8000/activity/recent
```

สิ่งที่ควรเห็น:

- `motion.motion_detected=true`
- `motion.occupancy_status` บอกว่ามีคนอยู่หรือกำลังเคลื่อนไหว
- `motion.recommendation` ให้คำแนะนำ เช่น เปิดไฟ/เปิดไมค์ต่อ หรือปิดไฟเมื่อไม่มี motion นาน
- `/activity/recent` มี event `motion_detected`

## Troubleshooting สั้น ๆ

Backend API ติดต่อไม่ได้:

```powershell
curl.exe http://127.0.0.1:8000/health
curl.exe https://<cloudflare-url>/health
```

ถ้า local ไม่ได้ ให้รัน `.\start_demo.ps1` ใหม่
ถ้า local ได้แต่ Cloudflare ไม่ได้ ให้รัน `.\stop_pwa_tunnel.ps1` แล้ว `.\start_pwa_tunnel.ps1`

PWA ยังใช้ URL เก่า:

- เปิด PWA Settings -> Backend API
- ใส่ Cloudflare URL ใหม่
- หรือเปิด URL แบบ `https://smart-home-ai-lyart.vercel.app/app?apiBase=https://xxxx.trycloudflare.com`

เสียง AI เงียบ:

```powershell
curl.exe http://127.0.0.1:8000/voice/status
```

ถ้า `audio_ready=false` ให้รอสักครู่หรือพูดใหม่ Edge TTS ต้องใช้อินเทอร์เน็ต

โมเดลตอบช้า:

- คำถามทั่วไปที่เข้า Ollama อาจใช้ 10-30 วินาทีในเครื่อง local
- `.\start_demo.ps1` จะ warmup ให้แล้ว แต่รอบแรกหลังเปิดคอมยังช้าได้
