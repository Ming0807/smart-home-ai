# Voice Node Task Board

## Update 2026-05-15 - Server-side board wake mode

- [x] Added Voice Node command types `wake_listen_start` and `wake_listen_stop`.
- [x] Added backend wake/session state for `voice-node-01`.
- [x] Added server-side wake phrase detection for `สวัสดีน้องฟ้า`, `หวัดดีน้องฟ้า`, `น้องฟ้า`.
- [x] Added sleep phrases so the board returns to idle wake listening: `ขอบคุณ`, `พอแล้ว`, `หยุดฟัง`, `เลิกคุย`, `น้องฟ้าพักก่อน`.
- [x] Updated firmware upload source to distinguish normal uploads from wake-listening uploads.
- [x] Added Web UI buttons to turn board wake listening on/off without touching browser mic.
- [x] Build and flash firmware to `voice-node-01`.
- [ ] Test: click `เปิด Wake บอร์ด`, say `สวัสดีน้องฟ้า`, continue one or two turns, then say `น้องฟ้าพักก่อน`.

## Update 2026-05-14 - Runtime tuning pass

- [x] Added backend runtime config updates for `voice-node-01` through `POST /voice-node/config`.
- [x] Added server config fields for mic gain, VAD enable, VAD threshold, min record time, and silence stop time.
- [x] Updated ESP-IDF firmware to refresh config from the server while in `WAKE_LISTENING`.
- [x] Updated firmware recording so gain and VAD values come from server config instead of requiring a reflash every time.
- [x] Added Web UI tuning controls for record seconds, mic gain, VAD threshold, and silence stop.
- [x] Updated `check_voice_node_report.ps1` to print the active Voice Node tuning values.
- [ ] Flash the runtime-tuning firmware to `voice-node-01`.
- [ ] Run a fresh 10-round report and adjust tuning from the Web UI if needed.

## Update 2026-05-15 - Continuous board conversation pass

- [x] Added Voice Node command types `conversation_start` and `conversation_stop`.
- [x] Added backend endpoints `POST /voice-node/commands/conversation-start` and `POST /voice-node/commands/conversation-stop`.
- [x] Updated firmware to parse `keep_mic_open` from `/assistant/audio`.
- [x] Added firmware continuous conversation mode: record -> upload -> play reply -> record again only when `keep_mic_open=true`.
- [x] Added Web UI buttons `เริ่มคุยผ่านบอร์ด` and `หยุดคุยผ่านบอร์ด`.
- [x] Built and flashed firmware to `voice-node-01` on COM10.
- [ ] Test with real speech: start board conversation, say `สวัสดี`, continue one more turn, then say `ขอบคุณ` or click stop.

Important:
- This does not touch browser mic.
- This is not full ESP-SR WakeNet yet. It is the safer hands-free conversation bridge before adding real wake word.
- Use the stop button if STT hears silence or keeps looping unexpectedly.

Suggested first tuning values:

```text
record_seconds=6
mic_record_gain=32
vad_enabled=true
vad_threshold=40
vad_silence_stop_ms=900
```

If many STT rounds are blank:
- keep the mic 10-20 cm from the mouth
- lower `vad_threshold` to 25-35
- increase `record_seconds` to 7

If the report says clipped:
- reduce `mic_record_gain` to 24
- move 20-30 cm away from INMP441

## Update 2026-05-12

- [x] Added per-upload WAV diagnostics on the server: duration, peak, RMS, clipping, silence, and quality notes.
- [x] Fixed test sentence tracking so each `record_once` command carries its own expected text instead of sharing one device-level value.
- [x] Clear history now also clears pending Voice Node test commands to avoid stale queued recordings.
- [x] Web UI now shows Audio OK, peak/RMS, and per-round quality badges in Voice Node Test.
- [x] `check_voice_node_report.ps1 -Details` now prints the last rounds with score and audio quality details.
- [ ] Run a fresh 10-round hardware test after this diagnostics pass.

## Update 2026-05-14

- [x] Emergency demo recovery: current notebook IP is `192.168.115.114`, while the last flashed firmware was targeting `192.168.160.114`.
- [x] Updated `firmware/voice_node_espidf/sdkconfig` to target `http://192.168.115.114:8000` for the next flash.
- [x] Added `fix_voice_node_ip_alias_admin.ps1` as a no-flash rescue path. Run it as Administrator to add the old firmware IP as a secondary Windows Wi-Fi IP.
- [x] Added Voice Node command TTL so stale record/play commands expire instead of running later after reconnect.
- [x] Disabled the `.env` STT initial prompt for now because a bad or over-specific prompt can make Whisper blank out more often.
- [x] Added one STT retry without VAD when the first Faster-Whisper pass returns no speech.
- [x] Patched the existing app binary server URL with a corrected checksum/hash and flashed it through COM10 because ESP-IDF build dependencies were incomplete.
- [x] Verified `voice-node-01` is online again at IP `192.168.115.226` and accepts queued `speaker_test` commands.
- [x] Added Voice Node transcript normalization before intent routing for common clipped-audio mistakes: `รดติด` -> `รถติด`, `กรุ่งเทพ` -> `กรุงเทพ`, `ความชื่น` -> `ความชื้น`, `มองร้อนมั้ย` -> `ห้องร้อนไหม`, and `หาว/คาวล่าสุด` -> `ข่าวล่าสุด`.
- [x] Set next firmware mic gain target to `MIC_RECORD_GAIN=32` because the latest reports showed uploaded audio peaking near 100%.
- [x] Rebuilt and flashed Voice Node on COM10 with `MIC_RECORD_GAIN=32`.
- [x] Cleared old Voice Node audio history after flashing so the next report measures the new firmware only.
- [ ] Run a fresh 10-round report with the new gain. If the report still says clipped, move 20-30 cm away from INMP441.

อัปเดตล่าสุด: 2026-05-11

## อัปเดตรอบล่าสุด

- [x] ปรับเสียงตอบกลับจากบอร์ดให้สรุปข่าวแบบสั้น อ่านออกเสียงไม่ตัดกลางรายการ
- [x] รองรับคำพูดเพี้ยนจาก STT เช่น `ข้าว LINE` ให้ตีความเป็นคำสั่งส่งข่าวเข้า LINE ได้
- [x] เพิ่ม cue ก่อนอัดเสียง: บอร์ดจะส่งเสียงติ๊ดสั้น ๆ แล้วหน่วงเล็กน้อยก่อนเริ่มอัด
- [x] เพิ่มระยะอัดเสียงสูงสุดจาก 4 วินาทีเป็น 6 วินาที โดยยังใช้ VAD หยุดเองเมื่อพูดจบ
- [x] build และ flash firmware ลง `voice-node-01` ผ่าน COM10 แล้ว
- [x] เพิ่ม `GET /voice-node/audio/history` สำหรับดูผลทดสอบเสียง 10 รอบล่าสุด
- [x] เพิ่มประวัติทดสอบเสียงใน Web UI เพื่อดู STT ดิบ / intent / playback ของแต่ละรอบ
- [x] เพิ่มตัวเลือกประโยคทดสอบและคะแนน STT similarity เพื่อวัดคุณภาพการถอดเสียงแบบเป็นตัวเลข
- [x] เพิ่ม `GET /voice-node/audio/report` สรุป STT success, คะแนนเฉลี่ย, playback success และสถานะพร้อมเดโม
- [x] เพิ่ม `DELETE /voice-node/audio/history` และปุ่มล้างประวัติใน Web UI สำหรับเริ่มรอบเทสใหม่
- [x] เพิ่ม `check_voice_node_report.ps1` สำหรับดูรายงาน Voice Node จาก PowerShell

## วิธีเทส Voice Node รอบใหญ่

1. เปิดหน้าเว็บ `http://127.0.0.1:8000`
2. ไปที่การ์ด `Voice Node Test`
3. กด `ล้างประวัติ` ก่อนเริ่มรอบใหม่
4. เลือกประโยคในช่อง `ประโยคที่จะพูดรอบนี้`
5. กด `อัดเสียง 1 รอบ`
6. รอเสียงติ๊ดสั้น แล้วพูดประโยคที่เลือก
7. รอให้บอร์ดอัปโหลดเสียง / server แปลง STT / บอร์ดเล่นเสียงตอบกลับ
8. ทำซ้ำให้ครบอย่างน้อย 5-10 ประโยค
9. ดู `รายงานทดสอบ`:
   - `STT` ควรเกิน 80%
   - `Score` ควรเกิน 70% เมื่อเลือกประโยคทดสอบ
   - `Playback` ควรเกิน 80%
   - ถ้าขึ้น `พร้อมเดโม` ถือว่าผ่านรอบแรก

เช็คจาก PowerShell ได้ด้วย:

```powershell
.\check_voice_node_report.ps1
```

เอกสารนี้ใช้ติดตามงาน Phase 2 ของ `voice-node-01` เพื่อให้เห็นชัดว่าอะไรทำไปแล้ว อะไรกำลังทำ และอะไรยังเหลือ โดยไม่กระทบ Phase 1 ที่ใช้งานผ่าน Web UI / browser mic / control node ได้ดีอยู่แล้ว

## สถานะรวม

- Phase 1 control node: เสถียร ใช้ต่อเป็นระบบหลักและ fallback
- Browser mic: ใช้งานดีและยังเป็นช่องทาง voice ที่แม่นที่สุดตอนนี้
- Voice Node ESP32-S3: เชื่อม server ได้, อัดเสียงได้, ส่งเสียงเข้า server ได้, เล่นเสียงตอบกลับจาก server ได้
- งานที่กำลังปรับ: ความแม่นของ STT จาก INMP441 และความเสถียรของ full loop

## ทำเสร็จแล้ว

- [x] สร้าง backend contract สำหรับ Voice Node
- [x] เพิ่ม `POST /voice-node/heartbeat`
- [x] เพิ่ม `GET /voice-node/config`
- [x] เพิ่ม `GET /voice-node/status`
- [x] เพิ่ม `POST /assistant/audio`
- [x] เพิ่ม `GET /voice-node/audio/current.wav`
- [x] เพิ่ม `GET /voice-node/audio/uploaded`
- [x] เพิ่ม command queue สำหรับ `speaker_test`
- [x] เพิ่ม command queue สำหรับ `record_once`
- [x] เพิ่ม command queue สำหรับ `play_audio`
- [x] สร้าง firmware ESP-IDF skeleton
- [x] เชื่อม Wi-Fi
- [x] ส่ง heartbeat ไป server
- [x] อ่าน INMP441 ผ่าน I2S
- [x] อัด WAV 16 kHz 16-bit mono
- [x] upload WAV ไป server
- [x] เล่นเสียงผ่าน MAX98357A
- [x] stream WAV reply จาก server ไปบอร์ด
- [x] เพิ่ม Voice Node panel ใน Web UI
- [x] เพิ่มปุ่มทดสอบอัดเสียงจาก UI
- [x] เพิ่มปุ่มทดสอบเสียงพูดจาก UI
- [x] เพิ่ม telemetry playback: stage, ok, error, audio size
- [x] build firmware ผ่าน
- [x] flash firmware ลงบอร์ดผ่าน COM10 ผ่าน

## กำลังทำ

- [x] ปรับ STT จาก INMP441 ให้แม่นขึ้นรอบแรก
- [x] เพิ่ม Thai STT prompt / domain vocabulary
- [x] เพิ่ม beam search ให้ faster-whisper
- [x] normalize เสียง WAV จากบอร์ดก่อนส่งเข้า STT
- [x] แก้คำเพี้ยนเฉพาะ domain เช่น `ข้าว` -> `ข่าว` เมื่อบริบทเป็นข่าว
- [x] เพิ่ม `STT ดิบ` ใน Voice Node panel เพื่อเทียบก่อน/หลัง correction
- [x] ลด firmware mic gain จาก 128 เป็น 64
- [x] เพิ่ม VAD threshold จาก 12 เป็น 40 เพื่อลด noise ถูกมองเป็น speech
- [x] แก้ server IP ใน firmware เป็น IP ปัจจุบันของเครื่อง
- [ ] ทดสอบคำพูดจริงหลายชุดผ่าน UI

## เหลือก่อนถือว่า Voice Node รอบแรกพร้อมเดโม

- [ ] วัด STT accuracy จากคำทดสอบอย่างน้อย 10 ประโยค
- [ ] ปรับ gain / ระยะไมค์ / record duration ให้เหมาะกับห้องจริง
- [ ] เพิ่ม serial/debug ที่อ่านง่ายสำหรับ mic RMS และ playback result
- [ ] ทดสอบ full loop 5-10 รอบติดกัน
- [ ] ทดสอบ fallback เมื่อ STT ไม่ได้ยินเสียง
- [ ] ทดสอบ fallback เมื่อ server/LLM ช้า
- [ ] ยืนยันว่า browser mic และ Phase 1 ไม่พัง
- [ ] commit baseline เมื่อผู้ใช้เทสผ่านแล้วเท่านั้น

## งานถัดไปหลัง STT ดีพอ

- [ ] เพิ่ม wake word จริงด้วย ESP-SR / WakeNet
- [ ] เพิ่ม VAD ที่ดีกว่า fixed record window
- [ ] ทำ streaming audio upload เพื่อลด latency
- [ ] ปรับ echo/feedback control ระหว่างลำโพงเล่นเสียง
- [ ] เพิ่ม config หน้าเว็บสำหรับ Voice Node
- [ ] เพิ่ม test script สำหรับ firmware + backend integration

## คำทดสอบ STT แนะนำ

ให้พูดใกล้ INMP441 ในระยะ 10-20 ซม. ก่อน แล้วค่อยขยับไกลขึ้น:

1. สวัสดีน้องฟ้า
2. วันนี้มีข่าวอะไรบ้าง
3. ข่าวระหว่างสหรัฐกับอิหร่านล่าสุดเป็นยังไง
4. ส่งข่าวเข้าไลน์ให้หน่อย
5. เปิดไฟให้หน่อย
6. ปิดไฟให้หน่อย
7. ห้องร้อนไหม
8. ความชื้นเท่าไหร่
9. ในกรุงเทพรถติดไหม
10. ไปสนามบินใช้เวลากี่นาที

## เกณฑ์ผ่านรอบ STT

- คำสั่งบ้านต้องจับใจความได้ถูกอย่างน้อย 8/10 รอบ
- คำว่า `ข่าว` ต้องไม่เพี้ยนเป็น `ข้าว` ในบริบทข่าว
- ถ้าเพี้ยนเล็กน้อย แต่ intent ยังถูกและระบบตอบถูก ถือว่าผ่านสำหรับเดโม
- ถ้า browser mic ยังแม่นกว่า ให้คง browser mic เป็นตัวหลักสำหรับ presentation และใช้ Voice Node เป็น hardware demo channel
