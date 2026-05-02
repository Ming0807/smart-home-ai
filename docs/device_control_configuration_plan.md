# แผนงาน Device Registry และหน้า UI ตั้งค่าอุปกรณ์ในบ้าน

## 1. เป้าหมาย

ยกระดับระบบควบคุมอุปกรณ์จากการสั่ง relay channel 1 แบบตายตัว ให้กลายเป็นระบบที่ผู้ใช้ตั้งค่าอุปกรณ์ได้เองผ่านหน้าเว็บ เช่น กำหนดว่า GPIO ใดคือไฟ พัดลม ปลั๊ก หรือเซนเซอร์ แล้วให้ AI เข้าใจคำสั่งธรรมชาติและสั่งงานอุปกรณ์นั้นได้อย่างปลอดภัย

แนวคิดหลักคือ:
- ผู้ใช้เป็นคนระบุ pin / channel / ชื่ออุปกรณ์ให้ถูกต้องในหน้าเว็บ
- Server เก็บข้อมูลอุปกรณ์ไว้ใน Device Registry
- Intent Router และ Device Control Service อ่านข้อมูลจาก Registry แทนการ hardcode คำว่าเปิดไฟ/ปิดไฟ
- ESP32 รับคำสั่งตาม config ที่ server รู้จัก และแจ้งผลกลับหลังทำงานจริง
- AI ต้องตรวจสอบสถานะจริงก่อนสั่งงาน เช่น บอร์ดออนไลน์ไหม อุปกรณ์เปิดอยู่แล้วไหม มี command ค้างอยู่ไหม

## 2. ปัญหาของระบบปัจจุบัน

จากโครงสร้างปัจจุบัน ระบบควบคุมอุปกรณ์ยังเหมาะกับ demo ระยะแรก แต่ยังไม่พอสำหรับการใช้งานจริง:

1. `device_control.py` ตรวจแค่คำว่าเปิด/ปิด แล้ว enqueue relay channel 1
2. ระบบยังไม่รู้ว่า relay channel 1 คือไฟ พัดลม หรืออุปกรณ์อะไรจริง ๆ
3. ยังไม่มีสถานะอุปกรณ์จริง เช่น `on`, `off`, `unknown`, `pending`
4. ยังไม่มี command acknowledgement จาก ESP32 หลังทำคำสั่งสำเร็จ
5. Intent Router ยังมี keyword hardcoded จึงเพิ่มอุปกรณ์ใหม่แล้ว AI ยังไม่รู้จักเอง
6. Dashboard แสดงสถานะพื้นฐานได้ แต่ยังไม่มีหน้าแยกสำหรับจัดการอุปกรณ์และ GPIO

## 3. แนวทางที่ดีที่สุด

ไม่ควรให้ LLM จำ mapping ของ pin โดยตรงใน prompt เพราะจะเสี่ยงต่อการ hallucinate และแก้ไขยาก

ทางที่ดีที่สุดคือสร้างชั้นกลางชื่อ **Device Registry** เป็น source of truth ของอุปกรณ์ทั้งหมด

โครงสร้างการทำงานที่แนะนำ:

```text
Web UI Device Settings
  -> Backend Device Config API
  -> Device Registry / Home State Service
  -> Intent Router + Entity Resolver
  -> Device Control Service
  -> ESP32 Command Queue
  -> ESP32 Applies Command
  -> ESP32 Command Result / Ack
  -> Server Updates Real Device State
  -> Chat + Dashboard Read Same State
```

## 4. Device Registry ควรเก็บอะไร

ข้อมูลที่ควรเก็บต่ออุปกรณ์:

```json
{
  "id": "living_room_light",
  "display_name": "ไฟห้องนั่งเล่น",
  "type": "relay",
  "room": "ห้องนั่งเล่น",
  "device_id": "esp32-01",
  "gpio_pin": 6,
  "relay_channel": 1,
  "active_low": true,
  "aliases": ["ไฟ", "ไฟห้องนั่งเล่น", "หลอดไฟ"],
  "actions": ["on", "off"],
  "state": "unknown",
  "enabled": true,
  "last_command_id": null,
  "last_updated_at": null
}
```

ข้อมูลที่ควรเก็บต่อบอร์ด:

```json
{
  "device_id": "esp32-01",
  "name": "ESP32-S3 หลัก",
  "board_type": "esp32-s3",
  "online": true,
  "last_seen_at": "2026-04-30T20:00:00Z",
  "capabilities": ["relay", "dht22", "pir"],
  "reserved_pins": [16, 17, 18],
  "config_version": 1
}
```

## 5. หน้า UI ที่ควรเพิ่ม

ควรแยกจากหน้า dashboard หลักเป็นหน้าใหม่ เช่น:

```text
GET /devices
```

หรือใน frontend:

```text
Dashboard
Device Settings
System Status
```

### 5.1 Device Settings Page

ควรมีส่วนหลักดังนี้:

1. **รายการอุปกรณ์**
   - ชื่ออุปกรณ์
   - ห้อง
   - ประเภท เช่น relay, sensor, switch
   - GPIO / relay channel
   - สถานะล่าสุด
   - online/offline ของบอร์ดที่ผูกอยู่

2. **เพิ่มอุปกรณ์**
   - Device name: เช่น ไฟโต๊ะ, พัดลมห้องนอน
   - Type: relay / sensor / virtual
   - Board: esp32-01
   - GPIO pin หรือ relay channel
   - Active low / active high
   - Aliases: คำที่ผู้ใช้อาจพูด เช่น ไฟ, หลอดไฟ, ไฟโต๊ะ

3. **ทดสอบอุปกรณ์**
   - ปุ่มเปิด
   - ปุ่มปิด
   - แสดง command status: queued, sent, applied, failed
   - แสดงคำเตือนถ้าบอร์ด offline

4. **คำสั่งที่ AI เข้าใจ**
   - แสดงตัวอย่างอัตโนมัติ เช่น
     - เปิดไฟโต๊ะ
     - ปิดไฟโต๊ะ
     - ไฟโต๊ะเปิดอยู่ไหม

5. **Pin Safety Warning**
   - แจ้งเตือนว่า server ตรวจได้เฉพาะรูปแบบ pin และ pin ซ้ำ
   - ผู้ใช้ยังต้องตรวจ wiring จริงเอง
   - ถ้าใช้ไฟบ้าน ต้องระวังเป็นพิเศษและควรใช้ relay module ที่ปลอดภัย

## 6. Backend API ที่ควรเพิ่ม

### 6.1 Device Config API

```text
GET /devices
POST /devices
GET /devices/{device_id}
PATCH /devices/{device_id}
DELETE /devices/{device_id}
```

ใช้สำหรับจัดการ registry

### 6.2 Device Command API

```text
POST /devices/{device_id}/command
GET /devices/status
```

ใช้สำหรับสั่งเปิด/ปิดจาก UI โดยไม่ต้องผ่าน chat

### 6.3 ESP32 Config / Ack API

```text
GET /esp32/config
POST /esp32/command-result
POST /esp32/capabilities
```

ใช้ให้ ESP32:
- โหลด config ล่าสุดจาก server
- แจ้งว่า command ทำสำเร็จหรือไม่
- แจ้งว่าบอร์ดรองรับ hardware อะไรบ้าง

## 7. Command Lifecycle ที่ควรมี

คำสั่งควบคุมอุปกรณ์ควรมีสถานะชัดเจน:

```text
created -> queued -> sent_to_esp32 -> applied -> confirmed
                              └── failed
                              └── timeout
```

ตัวอย่าง command:

```json
{
  "command_id": "cmd_20260430_001",
  "type": "relay",
  "target_device_id": "living_room_light",
  "esp32_device_id": "esp32-01",
  "relay_channel": 1,
  "gpio_pin": 6,
  "action": "on",
  "status": "queued",
  "created_at": "2026-04-30T20:00:00Z"
}
```

ESP32 ควรตอบกลับ:

```json
{
  "device_id": "esp32-01",
  "command_id": "cmd_20260430_001",
  "status": "applied",
  "state": "on",
  "timestamp": "2026-04-30T20:00:03Z"
}
```

## 8. AI ควรรู้จักอุปกรณ์ใหม่อย่างไร

AI ไม่ควรรู้ pin จาก prompt โดยตรง แต่ควรรู้ผ่าน service:

1. User พูดว่า “เปิดไฟโต๊ะ”
2. Intent Router จับว่าเป็น `device_control`
3. Entity Resolver หา target จาก Device Registry
   - `ไฟโต๊ะ` -> `living_room_light`
4. Device Control Service ตรวจสถานะ
   - บอร์ดออนไลน์ไหม
   - อุปกรณ์ enabled ไหม
   - state ปัจจุบันคืออะไร
   - มี pending command ไหม
5. ถ้าผ่าน จึง enqueue command
6. AI ตอบตามสถานะจริง

ตัวอย่างคำตอบ:

```text
ไฟโต๊ะเปิดอยู่แล้วนะ
```

```text
ตอนนี้บอร์ด ESP32 ไม่ออนไลน์ เลยยังสั่งเปิดไฟโต๊ะไม่ได้
```

```text
ส่งคำสั่งเปิดไฟโต๊ะให้แล้ว กำลังรอ ESP32 ยืนยันผล
```

## 9. Intent Router ควรปรับอย่างไร

จากเดิมที่มี keyword hardcoded เช่น `เปิดไฟ`, `ปิดไฟ`, ควรเปลี่ยนเป็น hybrid:

1. Fast rule สำหรับ action สำคัญ:
   - เปิด
   - ปิด
   - สถานะ
   - ทำงานไหม

2. Dynamic alias จาก Device Registry:
   - ไฟโต๊ะ
   - พัดลมห้องนอน
   - ปลั๊กคอม
   - ชื่อที่ผู้ใช้ตั้งเอง

3. LLM fallback สำหรับประโยคกำกวม:
   - “มันมืดจัง”
   - “ร้อนมากเลย”
   - “ช่วยทำให้ห้องสว่างหน่อย”

LLM fallback ควรคืนผลแบบ structured เช่น:

```json
{
  "intent": "device_control",
  "action": "on",
  "target_alias": "ไฟ",
  "confidence": 0.78
}
```

แต่ command จริงยังต้องผ่าน Device Control Service เสมอ

## 10. Storage ที่แนะนำ

ระยะสั้น:
- ใช้ JSON file ใน `data/` ได้ ถ้าต้องการเร็วและ demo-friendly

ระยะที่เหมาะกว่า:
- ใช้ SQLite เพื่อเก็บ device registry, command history, sensor history และ user preferences

แนะนำให้เริ่มด้วย SQLite ถ้าจะทำจริงจัง เพราะต่อยอดง่ายกว่า:

```text
devices
device_aliases
device_states
device_commands
esp32_boards
sensor_readings
automation_rules
```

## 11. ลำดับ implementation ที่ดีที่สุด

### Step 1: Device Registry Service

สร้าง service กลางสำหรับอ่าน/เขียนอุปกรณ์:

```text
server/services/device_registry.py
server/models/device.py
```

เริ่มจาก in-memory หรือ JSON ก่อนก็ได้ แต่ schema ต้องพร้อมย้ายไป SQLite

### Step 2: Device Status v2

รวมสถานะ:
- board online/offline
- relay state
- pending command
- last applied command
- sensor freshness

### Step 3: Command Ack

เพิ่ม:

```text
POST /esp32/command-result
```

และให้ ESP32 แจ้งกลับหลังเปิด/ปิด relay สำเร็จ

### Step 4: Device Control อ่านจาก Registry

เปลี่ยน `device_control.py` ให้:
- resolve อุปกรณ์จาก alias
- ตรวจ online
- ตรวจ state ปัจจุบัน
- ป้องกันสั่งซ้ำ
- สร้าง command_id
- update lifecycle

### Step 5: Device Settings UI

เพิ่มหน้า UI สำหรับ:
- เพิ่มอุปกรณ์
- ตั้ง GPIO / channel
- ตั้ง alias
- ทดสอบเปิด/ปิด
- ดูสถานะ command

### Step 6: Dynamic Intent

ให้ Intent Router โหลด alias จาก Registry เพื่อรู้จักอุปกรณ์ใหม่ทันที

### Step 7: SQLite Persistence

ถ้ายังเริ่มด้วย JSON ให้ย้ายมา SQLite เมื่อ flow ใช้งานได้แล้ว

### Step 8: Automation Rules

หลัง state นิ่งแล้วค่อยเพิ่ม rule เช่น:

```text
ถ้าอุณหภูมิ > 30 และมีคนอยู่ -> ถามว่าจะเปิดพัดลมไหม
ถ้า PIR ไม่เจอคน 10 นาที -> ปิดไฟอัตโนมัติ
```

## 12. สิ่งที่ไม่ควรทำตอนนี้

ยังไม่ควร:
- ให้ LLM เขียน/แก้ pin config เองโดยตรง
- ให้ LLM สั่ง GPIO โดยไม่ผ่าน service
- เพิ่ม framework frontend ขนาดใหญ่ทันที
- ทำ automation ซับซ้อนก่อนมี state และ ack
- ใช้ไฟบ้านจริงก่อนทดสอบ low voltage จนมั่นใจ

## 13. Definition of Done

ถือว่าแผนนี้สำเร็จเมื่อ:

1. ผู้ใช้เพิ่มอุปกรณ์จากหน้าเว็บได้
2. ผู้ใช้ตั้ง alias ได้ เช่น “ไฟโต๊ะ”
3. `/chat` เข้าใจคำสั่งจาก alias ใหม่
4. Server ตรวจว่า ESP32 online ก่อนสั่ง
5. Server ตรวจ state ก่อนสั่งซ้ำ
6. ESP32 แจ้งผล command กลับมา
7. Dashboard แสดง state ล่าสุดจริง
8. ถ้าอุปกรณ์ offline หรือ sensor stale ระบบตอบอย่างตรงไปตรงมา

## 14. ก้าวถัดไปที่แนะนำ

เริ่มจาก **Device Registry Service + Command Ack** ก่อน UI เต็มรูปแบบ

เหตุผล:
- เป็นแกนความถูกต้องของระบบ
- ทำให้ AI ไม่สั่งมั่ว
- ทำให้หน้า UI device settings มีข้อมูลจริงให้จัดการ
- ทำให้ demo ดูฉลาดและน่าเชื่อถือขึ้นทันที

หลังจากแกนนี้นิ่ง ค่อยทำหน้า UI ตั้งค่าอุปกรณ์แบบเต็ม จะไม่ต้องรื้อซ้ำหลายรอบ
