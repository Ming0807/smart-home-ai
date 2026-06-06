# Teacher Rubric Alignment

เอกสารนี้ใช้เทียบเกณฑ์ประเมินของอาจารย์กับรายงาน `report_AI_Smart_Home_Thai_Assistant_reviewed_v3.docx` และระบบจริงของโปรเจ็กต์

## ภาพรวม

รายงานของเราครอบคลุมเกณฑ์หลักค่อนข้างครบ และมีเนื้อหามากกว่าเกณฑ์ขั้นต่ำในหลายส่วน เช่น Voice Node, Browser Mic, TTS/STT, External APIs, LINE, Device Registry และ dashboard แต่เพื่อให้คะแนนอ่านง่ายขึ้น ควรเพิ่มตารางเทียบ rubric และหลักฐานทดสอบจริงประกอบ

สิ่งที่ไม่ควรลบ:

- รายละเอียด Voice Node และ Browser Mic
- รายละเอียด Weather/News/Navigation/Traffic/LINE
- รายละเอียด DHT22/PIR/Relay และ command queue
- ภาคผนวกทางเทคนิค

สิ่งที่ควรเพิ่ม:

- ตารางเทียบ rubric กับหัวข้อในรายงาน
- ภาพ/หลักฐานจริงของ dashboard และ hardware
- ผลทดสอบจริงล่าสุดจากสคริปต์
- คำอธิบาย protocol ที่ใช้จริง: HTTP REST, WebSocket, command polling
- ระบุว่า MQTT เป็นทฤษฎี/ทางเลือก ไม่ใช่ protocol หลักของระบบนี้

## เทียบเกณฑ์รายบท 30 คะแนน

| ส่วนที่ประเมิน | คะแนน | สถานะของเรา | จุดที่ควรเพิ่ม |
| --- | ---: | --- | --- |
| บทที่ 1 บทนำ | 4 | ครบ: ที่มา วัตถุประสงค์ ขอบเขต ประโยชน์ | เพิ่ม summary สั้น ๆ ว่ามี 2 บอร์ด: `esp32-01` และ `voice-node-01`, sensor/actuator ที่ใช้จริง และ platform ที่ใช้ |
| บทที่ 2 ทฤษฎีและงานวิจัย | 5 | ครบเกินขั้นต่ำ: ESP32-S3, FastAPI, Ollama, STT/TTS, DHT22, PIR, INMP441, MAX98357A | เพิ่ม subsection protocol: HTTP REST API, WebSocket, command polling, และระบุว่า MQTT เป็นทางเลือกแต่ไม่ได้ใช้เป็น protocol หลัก |
| บทที่ 3 วิธีดำเนินงาน/ออกแบบระบบ | 7 | ครบมาก: architecture, DFD, use case, sequence, deployment, state machine, wiring, UI, folder structure | ต้องแทนรูปที่ยังเป็น placeholder, เพิ่ม DFD หลายระดับ, ตรวจ pinout ให้ตรง hardware จริง |
| บทที่ 4 ผลทดลอง/วิเคราะห์ผล | 5 | มีผลพัฒนาและผลทดสอบหลายส่วน | ควรเพิ่มผลทดสอบจริงล่าสุดจาก `check_demo_status.ps1` และ `check_voice_node_report.ps1 -Details`, screenshot จริง, ตาราง response time/STT/uptime |
| บทที่ 5 สรุปและข้อเสนอแนะ | 4 | ครบ: สรุป ปัญหา อุปสรรค future work | เพิ่มข้อจำกัด RAM/MicroPython/Voice Node/STT/Network และแนวทางแก้ตามระบบจริง |
| ความสมบูรณ์รูปเล่ม/อ้างอิง | 5 | มีโครงรูปเล่มและบรรณานุกรม | ต้องกรอก placeholder, ตรวจ APA7, update field/เลขหน้า, ตรวจรูปไม่เสีย และไม่มี secret |

## เทียบเกณฑ์คุณภาพระบบ 30 คะแนน

| เกณฑ์ | คะแนน | สถานะของเรา | หลักฐาน/สิ่งที่ควรเพิ่ม |
| --- | ---: | --- | --- |
| 1. ระบบฮาร์ดแวร์ & MicroPython | 8 | ทำได้จริง: ESP32-S3 Control Node, DHT22, PIR, Relay, MicroPython, heartbeat/sensor/motion/command polling | เพิ่มรูปถ่าย wiring จริง, pinout table, memory/crash handling, reconnect behavior |
| 2. Web/Mobile App & การเชื่อมต่อ | 8 | แข็งแรง: Web Dashboard, Browser Mic, Voice Node panel, FastAPI REST, WebSocket diagnostic, real-time status | เพิ่ม screenshot จริง, อธิบาย protocol flow, response/fallback behavior, online/offline logic |
| 3. ความสมบูรณ์และความคิดสร้างสรรค์ | 6 | สูงกว่าเกณฑ์: AI Thai assistant, local LLM, voice conversation, TTS/STT, external APIs, LINE news | เพิ่ม demo scenario แบบ end-to-end และระบุ innovation ให้ชัด เช่น browser fallback + hardware voice node |
| 4. สถาปัตยกรรมและความปลอดภัย | 4 | มี architecture, env config, no hardcoded secrets ในรายงาน, fallback, cache | เพิ่มข้อควรระวัง Wi-Fi credentials, API keys ผ่าน `.env`, network LAN only, future auth |
| 5. ต่อยอดเชิงธุรกิจ/ใช้งานจริง | 4 | มี future work หลายข้อ | เพิ่ม use cases บ้าน/หอพัก/ผู้สูงอายุ/ห้องเรียน, maintenance plan, SQLite persistence, multi-device config |

## Gap ที่ควรจัดการก่อนส่ง

- [ ] กรอกข้อมูลหน้าปกและใบรับรองที่ยังเป็น placeholder
- [ ] สร้าง/แทนรูป DFD ให้ถูกระดับ: Context Diagram, DFD Level 1, DFD Level 2
- [ ] แทน screenshot dashboard จริงในบทที่ 4
- [ ] ถ่ายภาพ hardware จริงทั้งหมด
- [ ] อัปเดตผลทดสอบล่าสุดด้วยสคริปต์จริง
- [ ] ตรวจว่าไม่มี API key หรือ secret ในรายงาน
- [ ] ตรวจ APA7 และ update field ใน Word

## ข้อเสนอเชิงกลยุทธ์

ให้คงรายงานเดิมไว้เพราะเนื้อหาแน่นและเกินเกณฑ์ แต่เพิ่มภาคผนวกหรือหัวข้อท้ายบทที่ 5 ชื่อ “ตารางเทียบเกณฑ์การประเมินกับระบบที่พัฒนา” เพื่อช่วยให้อาจารย์ตรวจง่ายและเห็นว่าระบบตอบโจทย์ rubric ครบ
