# Report Review Tasks

เอกสารนี้คือ checklist สำหรับตรวจรายงาน `report_AI_Smart_Home_Thai_Assistant_reviewed_v3.docx` ให้ตรงกับระบบจริงก่อนส่งหรือใช้นำเสนอ

## สถานะที่แก้แล้วในฉบับ reviewed

- [x] ปรับบทคัดย่อให้ตรงกับระบบปัจจุบัน: ใช้ Gemma 4 E2B ผ่าน Ollama เป็นโมเดลหลักเดโม และ Typhoon 2 8B เป็นทางเลือก
- [x] แก้คำอธิบาย Local ให้ชัดเจนว่า core AI/IoT ทำงาน local แต่ weather/news/navigation/traffic/LINE/Edge TTS ต้องใช้อินเทอร์เน็ต
- [x] เพิ่มหมายเหตุสถานะระบบจริงล่าสุดของ Control Node, Voice Node, Browser Mic และ wake handoff
- [x] ลดการ overclaim เรื่องระบบเสร็จสมบูรณ์ทั้งหมด ให้เป็น demo-ready พร้อมรายการที่ควรพัฒนาต่อ
- [x] ปรับตาราง/ข้อความสำคัญบางส่วนที่ยังอ้าง Typhoon เป็นโมเดลหลัก
- [x] เพิ่มรายการตรวจแก้และงานต่อยอดไว้ท้ายรายงาน

## งานที่ผู้จัดทำต้องเติมเอง

- [ ] กรอกชื่อผู้จัดทำ
- [ ] กรอกชื่ออาจารย์ที่ปรึกษา
- [ ] กรอกชื่อสาขา คณะ มหาวิทยาลัย และชื่อปริญญา
- [ ] กรอกข้อมูลคณะกรรมการสอบหรือหน้าอนุมัติตามรูปแบบสถาบัน
- [ ] ตรวจเลขหน้า สารบัญ สารบัญตาราง และสารบัญภาพ หลังเปิดไฟล์ใน Word แล้วกด Update Field

## งานตรวจข้อเท็จจริงก่อนส่งรายงาน

- [ ] รัน `.\check_demo_status.ps1` แล้วบันทึกสถานะ server, Ollama, web UI, Control Node และ Voice Node ล่าสุด
- [ ] รัน `.\check_voice_node_report.ps1 -Details` แล้วอัปเดตผลทดสอบ Voice Node ถ้าตัวเลขต่างจากในรายงาน
- [ ] ยืนยันว่า `.env` เครื่องนำเสนอใช้ `OLLAMA_MODEL=gemma4:e2b`
- [ ] ยืนยันว่า OpenWeather, Currents, OpenRouteService, TomTom และ LINE ใช้ API key ผ่าน environment variables เท่านั้น
- [ ] ทดสอบ browser mic เป็น fallback หลักก่อนวันนำเสนอ
- [ ] ทดสอบ Voice Node board-talk และ wake handoff อย่างน้อย 5-10 รอบในห้องจริง
- [ ] ทดสอบ Control Node: heartbeat, DHT22, PIR, relay command queue

## งานปรับรายงาน/ภาพประกอบ

- [ ] อัปเดต screenshot Web UI ให้ตรงกับหน้าปัจจุบัน
- [ ] เพิ่มภาพ Voice Node panel ที่แสดงสถานะ wake/board-talk/audio history
- [ ] เพิ่มภาพ Device Configuration หรือ Device Registry ถ้าจะพูดเรื่องกำหนด GPIO ผ่านหน้าเว็บ
- [ ] ตรวจ diagram ให้แยกชัดเจนระหว่าง Browser Mic, Control Node และ Voice Node
- [ ] ตรวจว่าไม่มี secret หรือ API key จริงปรากฏในรายงาน

## งานพัฒนาต่อที่ควรระบุเป็น Future Work

- [ ] เพิ่ม SQLite persistence สำหรับ sensor, command queue, chat memory และ voice node history
- [ ] เพิ่ม device state verification ก่อนสั่งงาน เช่น บอร์ดออนไลน์ไหม รีเลย์เปิดอยู่แล้วไหม sensor ล่าสุดสดพอไหม
- [ ] เพิ่ม conversation memory สำหรับข่าวและคำสั่งต่อเนื่อง เช่น "อ่านข้อ 2" หรือ "ส่งเข้า LINE"
- [ ] ปรับปรุง Voice Node STT ด้วย noise reduction/VAD tuning ก่อนพิจารณา streaming production mode
- [ ] ประเมิน ESP-SR/WakeNet หรือ wake word เฉพาะอุปกรณ์ในอนาคต
- [ ] เพิ่ม unit/integration tests สำหรับ intent routing, device control, sensor status, external API fallback และ voice-node endpoints

## เกณฑ์พร้อมนำเสนอ

- [ ] Browser mic คุยต่อเนื่องได้เสถียร
- [ ] Voice Node รับคำสั่งสั้น ๆ และเล่นเสียงตอบกลับได้
- [ ] ถ้า Voice Node มีปัญหา ระบบยัง demo ได้ผ่าน Web UI/browser mic
- [ ] คำถามหลักตอบได้ครบ: sensor, relay, weather, news, traffic/navigation, LINE news, system status
- [ ] รายงานไม่มี placeholder สำคัญและไม่มีข้อมูลลับ
