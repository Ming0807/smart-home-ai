# Development Rules, Best Practices & Performance Guide

## 1. วัตถุประสงค์เอกสาร
เอกสารนี้ใช้เป็นมาตรฐานการพัฒนาโปรเจ็กต์ AI Smart Home เพื่อให้โค้ดมีคุณภาพ ดูแลง่าย ขยายต่อได้ และทำงานได้เร็ว เสถียร พร้อมสำหรับการสาธิตและใช้งานจริง

---

## 2. หลักการพัฒนาหลัก (Core Engineering Rules)

### 2.1 Readability First
- โค้ดต้องอ่านง่ายก่อนฉลาด
- ใช้ชื่อฟังก์ชัน/ตัวแปรสื่อความหมายชัดเจน
- หลีกเลี่ยง logic ซ้อนลึกเกินไป

### 2.2 Single Responsibility Principle
- 1 module ควรมีหน้าที่หลักเดียว
- route ไม่ควรมี business logic หนัก
- service ไม่ควรปะปน UI code

### 2.3 Config Driven
- ค่า config ทั้งหมดเก็บในไฟล์ `.env` หรือ `config.py`
- ห้าม hardcode API key, path, GPIO pin, URL

### 2.4 Fail Gracefully
- ถ้า API ล่ม ระบบยังต้องตอบได้
- ถ้า AI ช้า ให้ fallback response
- ถ้า sensor offline ให้แจ้งสถานะ ไม่ crash

---

## 3. Code Structure Best Practices

## 3.1 แยก Layer ชัดเจน
```text
routes/      -> API endpoints
services/    -> business logic
models/      -> schema / db model
utils/       -> helper functions
prompts/     -> system prompts
```

## 3.2 Naming Convention
- snake_case สำหรับ Python function / variable
- PascalCase สำหรับ class
- UPPER_CASE สำหรับ constant

ตัวอย่าง:
```python
MAX_RESPONSE_TOKENS = 80
get_weather_data()
ConversationManager
```

## 3.3 File Size Rule
- 1 file ไม่ควรเกิน ~300-500 บรรทัด ถ้าเริ่มใหญ่ให้แยก module

---

## 4. Python Best Practices (Server)

## 4.1 ใช้ Type Hints
```python
def chat(message: str) -> dict:
```

## 4.2 ใช้ Pydantic Schema
ใช้ validate request/response ทุก endpoint

## 4.3 ใช้ Async เมื่อเหมาะสม
เหมาะกับ:
- เรียก API ภายนอก
- I/O งาน network
- file operations

## 4.4 หลีกเลี่ยง Blocking Code ใน Route
ไม่ควรทำ inference หนักใน route ตรงๆ โดยไม่จัดการ queue/thread

---

## 5. MicroPython Best Practices (ESP32)

## 5.1 Loop ต้องเบา
- หลีกเลี่ยง while True ที่กิน CPU โดยไม่ sleep

## 5.2 Retry Network
- ถ้า Wi-Fi หลุด ต้อง reconnect อัตโนมัติ

## 5.3 Watchdog Mindset
- ถ้าค้าง ให้ restart ได้เอง

## 5.4 Memory Conscious
- ใช้ object เท่าที่จำเป็น
- ล้างตัวแปรใหญ่เมื่อไม่ใช้

---

## 6. AI / LLM Best Practices

## 6.1 Prompt Management
- แยก prompt ไว้ไฟล์ภายนอก
- version control prompt

## 6.2 Keep Context Short
- ส่ง history เท่าที่จำเป็น
- สรุปบทสนทนาเก่าแทนส่งทั้งหมด

## 6.3 Response Guardrails
- จำกัด max_tokens
- บังคับ style การตอบ
- กัน hallucination ด้วย tool routing

## 6.4 Use Right Tool for Right Job
- คำสั่ง IoT ง่ายๆ ใช้ rule-based ก่อน
- ข้อมูลสดใช้ API
- คุยทั่วไปใช้ LLM

---

## 7. Performance Rules (สำคัญ)

## 7.1 Speed First During Demo
- warm-up model ก่อน present
- preload config
- เปิดเฉพาะ service จำเป็น

## 7.2 Use Quantized Model
- Typhoon 8B ใช้ Q4/Q5

## 7.3 Streaming Response
- แสดงผลทีละ token

## 7.4 Cache Frequently Asked Queries
เช่น:
- วันนี้อากาศยังไง
- เวลาปัจจุบัน
- ข่าววันนี้

## 7.5 Route Before LLM
- ถ้ารู้ว่าเป็น weather query อย่าส่งเข้า model ก่อน

## 7.6 Limit Token Output
```python
max_tokens = 80
```

## 7.7 Concurrency Control
- จำกัดจำนวน request พร้อมกัน
- ใช้ queue ถ้าจำเป็น

---

## 8. Stability Rules

## 8.1 Timeout ทุก External API
```python
timeout = 5
```

## 8.2 Retry Strategy
- retry 1-2 ครั้งพอ
- exponential backoff

## 8.3 Logging ทุก Critical Event
- API fail
- device command fail
- model error

## 8.4 Health Check Endpoints
```text
GET /health
GET /ready
```

---

## 9. Security Rules

## 9.1 เก็บ API Key ใน .env เท่านั้น

## 9.2 Validate Input เสมอ
- ป้องกัน malformed request

## 9.3 จำกัด Local Network Access ถ้าเป็นระบบในบ้าน

## 9.4 Sanitize Logs
- ไม่ log secret

---

## 10. Database Rules

## 10.1 Use SQLite Initially
- ง่าย เร็ว พอสำหรับโปรเจ็กต์

## 10.2 Keep Tables Simple
- conversations
- device_logs
- sensor_logs
- user_preferences

## 10.3 Index Queries ที่ใช้บ่อย

---

## 11. Frontend / UI Rules

## 11.1 Simple > Fancy
- UI ต้องเสถียรก่อนสวย

## 11.2 Realtime Feedback
- loading state
- typing indicator
- device status สด

## 11.3 One Click Demo Buttons
ปุ่ม preset:
- เปิดไฟ
- ห้องร้อนไหม
- ข้างนอกร้อนไหม
- ข่าววันนี้

---

## 12. Git / Workflow Rules

## 12.1 Branch Strategy
- main = stable
- dev = current work
- feature/* = feature ใหม่

## 12.2 Commit Format
```text
feat: add weather service
fix: relay timeout issue
perf: reduce prompt tokens
```

## 12.3 Backup Often
- backup config
- backup prompts
- backup db ก่อน demo

---

## 13. Testing Rules

## 13.1 Test Levels
- unit test service logic
- integration test API
- hardware test ESP32 separately
- end-to-end demo test

## 13.2 Demo Rehearsal
ทดสอบ scenario จริงอย่างน้อย 3 รอบก่อน present

---

## 14. Demo Day Checklist

- reboot เครื่องก่อนเริ่ม
- warm-up model
- internet พร้อม
- sensor online
- relay online
- speaker ดังพอดี
- backup hotspot
- backup script demo
- fallback text mode ถ้าเสียงมีปัญหา

---

## 15. Metrics ที่ควรวัด

- average response time
- weather API latency
- model token/sec
- command success rate
- uptime
- memory usage
- cpu usage

---

## 16. สิ่งที่ควรเพิ่มในอนาคต

- Docker deployment
- Redis cache
- PostgreSQL
- WebSocket realtime UI
- CI/CD pipeline
- Monitoring dashboard

---

## 17. Golden Rules สุดท้าย

1. Demo ต้องเสถียรก่อนสมบูรณ์แบบ
2. ถ้า rule-based เร็วกว่า ใช้มันก่อน
3. ใช้ LLM เฉพาะจุดที่จำเป็น
4. ทุกอย่างต้องมี fallback
5. ผู้ใช้ต้องรู้สึกว่าระบบเร็ว
6. โค้ดที่ maintain ได้ ชนะโค้ดที่ดูเทพ

