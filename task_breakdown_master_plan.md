# TASK BREAKDOWN MASTER PLAN

## 1. วัตถุประสงค์เอกสาร
เอกสารนี้ใช้เป็นแผนปฏิบัติงานหลักสำหรับโปรเจ็กต์ AI Smart Home Thai Assistant เพื่อให้สามารถพัฒนาได้เป็นขั้นตอน ลดความสับสน คุมเวลา และพร้อมส่งงาน/พรีเซนต์ได้จริง

---

## 2. เป้าหมายสุดท้าย (Final Deliverables)

ต้องมีครบ:
- ระบบ AI Smart Home ใช้งานได้จริง
- ESP32-S3 เชื่อม Server สำเร็จ
- ควบคุม Relay ได้
- อ่าน Sensor ได้
- AI คุยภาษาไทยได้
- ตอบข้อมูลภายนอกผ่าน API ได้
- ระบบเสียงตอบกลับได้
- Dashboard ใช้งานได้
- มีรายงาน
- มีสไลด์นำเสนอ
- มี Demo Script

---

## 3. Master Timeline (5 สัปดาห์)

## Week 1: Hardware Bring-up
เป้าหมาย: อุปกรณ์ทุกชิ้นใช้งานได้

### Tasks
- [ ] Flash MicroPython ลง ESP32-S3
- [ ] ต่อ Wi-Fi สำเร็จ
- [ ] ทดสอบ Serial console
- [ ] ทดสอบ DHT22
- [ ] ทดสอบ PIR Sensor
- [ ] ทดสอบ Relay Module
- [ ] ทดสอบ MAX98357A + Speaker
- [ ] ทดสอบเล่นเสียงง่ายๆ
- [ ] จัดสายบน breadboard ให้เรียบร้อย

### Deliverable
- ESP32 พร้อมใช้งานเต็มระบบ

---

## Week 2: Server Core + AI Chat
เป้าหมาย: AI คุยได้แล้ว

### Tasks
- [ ] ติดตั้ง Python environment
- [ ] ติดตั้ง FastAPI + Uvicorn
- [ ] ติดตั้ง llama.cpp / Ollama
- [ ] โหลด Typhoon 2 8B
- [ ] สร้าง endpoint POST /chat
- [ ] ทำ prompt ให้คุยเหมือนเพื่อน
- [ ] ทดสอบถามตอบทั่วไป
- [ ] ทำ logging เบื้องต้น

### Deliverable
- Chatbot ภาษาไทยใช้งานได้

---

## Week 3: IoT Integration
เป้าหมาย: AI คุมบ้านได้

### Tasks
- [ ] สร้าง POST /esp32/sensor
- [ ] สร้าง GET /esp32/commands
- [ ] ESP32 ส่ง sensor data เข้า server ได้
- [ ] Server ส่งคำสั่งกลับ ESP32 ได้
- [ ] AI เข้าใจคำสั่งเปิด/ปิดไฟ
- [ ] Relay ทำงานตามคำสั่ง
- [ ] AI ตอบจากข้อมูล sensor ได้

### Deliverable
- ผู้ใช้พูดว่า “ร้อนมาก” แล้วเปิดพัดลมได้

---

## Week 4: Voice + External APIs
เป้าหมาย: ฉลาดขึ้นและดูว้าว

### Tasks
- [ ] เพิ่ม Text-to-Speech
- [ ] ระบบตอบเสียงออกลำโพง
- [ ] เพิ่ม OpenWeather API
- [ ] เพิ่ม Google Maps / Traffic API
- [ ] เพิ่ม NewsAPI หรือ Web Search
- [ ] สร้าง Intent Router
- [ ] AI ตอบข้อมูลสดได้

### Deliverable
- ถามว่า “ฝนจะตกไหม” แล้วตอบได้

---

## Week 5: Dashboard + Polish + Demo Prep
เป้าหมาย: พร้อมพรีเซนต์

### Tasks
- [ ] ทำหน้า Dashboard
- [ ] แสดง sensor realtime
- [ ] แสดง device status
- [ ] แสดง chat history
- [ ] ปรับ performance
- [ ] warm-up model script
- [ ] เขียนสไลด์
- [ ] เขียนรายงาน
- [ ] ซ้อม demo 3 รอบขึ้นไป

### Deliverable
- พร้อมส่งงานและนำเสนอ

---

## 4. Daily Execution Order (ลำดับทำงานจริง)

ทุกครั้งที่นั่งทำงาน ให้ทำตามลำดับนี้:

1. เปิดเครื่อง / เช็กระบบ
2. เช็ก model โหลดได้
3. เช็ก ESP32 online
4. เช็ก sensor data เข้า server
5. ทำ task หลักวันนั้น 1 อย่าง
6. test ทันที
7. commit code
8. backup
9. note ปัญหาไว้

---

## 5. Task Priority Matrix

## P0 (ต้องเสร็จแน่)
- Chat AI
- Relay Control
- Sensor Read
- ESP32 ↔ Server
- Basic Demo

## P1 (ควรมี)
- Voice Output
- Weather API
- Dashboard
- Logging

## P2 (เสริม)
- Traffic API
- News API
- Memory Chat
- Voice Input

## P3 (Luxury)
- Face Recognition
- Multi-user Profiles
- Fancy UI Animations

---

## 6. หากเวลาน้อย ให้ตัดตามนี้

ตัดก่อน:
- Voice Input
- Traffic API
- News API
- Fancy UI
- Multi-user

ห้ามตัด:
- Chat AI
- Relay Demo
- Sensor Demo
- Stable Flow

---

## 7. Milestones สำคัญ

### M1
ESP32 ต่อ sensor ครบ

### M2
Typhoon ตอบได้

### M3
AI เปิดไฟได้

### M4
ถามอากาศได้

### M5
พูดออกลำโพงได้

### M6
พร้อม Present

---

## 8. Demo Script (ใช้วันจริง)

### Demo 1: คุยทั่วไป
ผู้ใช้: สวัสดี
AI: สวัสดี วันนี้เป็นยังไงบ้าง

### Demo 2: ควบคุมบ้าน
ผู้ใช้: เปิดไฟหน่อย
Relay ON

### Demo 3: Sensor Aware
ผู้ใช้: ห้องร้อนไหม
AI: ตอนนี้ 31 องศา ค่อนข้างร้อนนะ

### Demo 4: Outside World
ผู้ใช้: ฝนจะตกไหม
AI: วันนี้มีโอกาสฝนประมาณ 60% แนะนำพกร่ม

### Demo 5: Friendly Mode
ผู้ใช้: วันนี้เหนื่อยจัง
AI: พักก่อนก็ได้นะ เดี๋ยวเปิดไฟสบายตาให้

---

## 9. Folder Ownership (ถ้าทำหลายคน)

### คนที่ 1
ESP32 / Hardware

### คนที่ 2
Backend / API / Database

### คนที่ 3
AI / Prompt / LLM

### คนที่ 4
UI / Dashboard / Slides

---

## 10. Risks & Mitigation

## Risk: Model ช้า
Fix:
- ใช้ quantized model
- จำกัด token
- warm-up

## Risk: Wi-Fi หลุด
Fix:
- reconnect auto
- hotspot สำรอง

## Risk: Sensor เพี้ยน
Fix:
- average values
- fallback display

## Risk: API ล่ม
Fix:
- cache data
- fallback response

---

## 11. Final Week Checklist

- [ ] ระบบเปิดติดครั้งเดียวผ่าน
- [ ] ทุก endpoint ใช้งานได้
- [ ] เสียงดังพอดี
- [ ] AI ตอบเร็วพอ
- [ ] Demo script จำได้
- [ ] สไลด์เสร็จ
- [ ] รายงานเสร็จ
- [ ] backup ทั้งหมด

---

## 12. Golden Rule

ทำของที่ “เสถียรและโชว์ได้จริง” ดีกว่าของที่ใหญ่แต่พังหน้างาน

