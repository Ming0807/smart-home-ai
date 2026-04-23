# NEXT_TASKS

## 1. Purpose
This file is the execution backlog for AI coding agents and human developers.
Use it to decide what to build next in the highest-value order.

Rules:
- Complete tasks top-down unless priorities change.
- Mark done items.
- Keep tasks small and testable.
- Prefer shipping working increments.

---

## 2. Current Priority Strategy

Priority order:
1. Core project skeleton
2. Stable chat endpoint
3. Ollama / Typhoon integration
4. ESP32 connectivity
5. Device control
6. Sensor intelligence
7. External APIs
8. Voice system
9. Dashboard polish
10. Advanced memory / personalization

---

## 3. PHASE A — Foundation Setup

## A1. Create project folder structure
- [ ] Create folders:
  - server/
  - server/routes/
  - server/services/
  - server/models/
  - server/utils/
  - esp32/
  - webui/
  - docs/
  - data/

Deliverable:
- Clean scalable structure

## A2. Create Python environment
- [ ] requirements.txt or pyproject.toml
- [ ] install FastAPI, Uvicorn, Pydantic, requests, sqlalchemy

## A3. Create base FastAPI app
- [ ] `server/app.py`
- [ ] `/health`
- [ ] `/ready`

Deliverable:
- Server boots successfully

---

## 4. PHASE B — LLM Core Chat

## B1. Create llm_manager.py
- [ ] Support Ollama HTTP API
- [ ] Configurable model name
- [ ] Timeout handling
- [ ] Streaming optional

## B2. Create `/chat` endpoint
- [ ] Accept message input
- [ ] Call llm_manager
- [ ] Return structured JSON

## B3. Add system prompt loading
- [ ] Load prompt from prompts/system_prompt.txt

## B4. Add fallback handling
- [ ] If model unavailable, return graceful response

Deliverable:
- Stable Thai chatbot works locally

---

## 5. PHASE C — Intent Routing

## C1. Create intent_router.py
- [ ] Rule-based keyword routing first
- [ ] Detect:
  - device_control
n  - weather_query
  - traffic_query
  - sensor_query
  - general_chat

## C2. Connect `/chat` to router
- [ ] Route before LLM when possible

Deliverable:
- Faster smarter responses

---

## 6. PHASE D — ESP32 Integration

## D1. Create `/esp32/heartbeat`
- [ ] Device online status

## D2. Create `/esp32/sensor`
- [ ] Receive temperature
- [ ] humidity
- [ ] motion

## D3. Create `/esp32/commands`
- [ ] Polling command queue

## D4. Create ESP32 sample client code
- [ ] Wi-Fi connect
- [ ] send sensor data
- [ ] poll commands

Deliverable:
- ESP32 communicates with server

---

## 7. PHASE E — Device Control

## E1. Create device_control.py
- [ ] queue command for relay1
- [ ] queue command for relay2

## E2. Add chat commands
Examples:
- เปิดไฟ
- ปิดไฟ
- เปิดพัดลม
- ปิดพัดลม

## E3. Add confirmation responses

Deliverable:
- AI controls real hardware

---

## 8. PHASE F — Sensor Intelligence

## F1. Create sensor_manager.py
- [ ] Store latest values
- [ ] Compute freshness timestamp

## F2. Add sensor Q&A
Examples:
- ห้องร้อนไหม
- ตอนนี้ความชื้นเท่าไหร่

## F3. Add automation rules
- if temp > threshold -> suggest fan

Deliverable:
- AI aware of home environment

---

## 9. PHASE G — External APIs

## G1. weather_service.py
- [ ] OpenWeather integration

## G2. traffic_service.py
- [ ] Google Maps / route placeholder

## G3. news_service.py
- [ ] NewsAPI integration

## G4. cache layer
- [ ] 5-10 min cache for API responses

Deliverable:
- AI knows outside world

---

## 10. PHASE H — Voice System

## H1. tts_service.py
- [ ] Edge TTS Thai voices

## H2. `/voice/speak`
- [ ] text to mp3/wav

## H3. stt_service.py
- [ ] Whisper integration later

Deliverable:
- AI speaks Thai

---

## 11. PHASE I — Web UI

## I1. Basic dashboard
- [ ] chat box
- [ ] sensor panel
- [ ] device status

## I2. Chat UX
- [ ] typing indicator
- [ ] timestamps

## I3. Voice button
- [ ] speak response

Deliverable:
- Demo-ready interface

---

## 12. PHASE J — Performance & Stability

## J1. Warm-up script
- [ ] pre-call model on startup

## J2. Prompt optimization
- [ ] shorten prompt tokens

## J3. Logging
- [ ] latency
- [ ] errors
- [ ] command success

## J4. Timeout + fallback

Deliverable:
- Stable presentation mode

---

## 13. Immediate Next Task (Recommended Now)

Start here:

1. Create FastAPI skeleton
2. Add `/health`
3. Add `/chat`
4. Connect Ollama Typhoon
5. Test one Thai response

---

## 14. Prompt for Coding Agent

```text
Read AGENT_RULES.md first.
Read project markdown docs.
Implement NEXT_TASKS Phase A and Phase B only.
Make production-quality code.
Keep changes minimal and clean.
```

---

## 15. Done Log

Use this section to track progress.

- [ ] A1
- [ ] A2
- [ ] A3
- [ ] B1
- [ ] B2
- [ ] B3
- [ ] B4
- [ ] C1
- [ ] C2
...