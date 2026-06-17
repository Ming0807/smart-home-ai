# PWA Mobile Development Tasks

## Goal

Build a mobile-first PWA for Nong Fa that lets a user install the app on iOS or Android, use the phone microphone for voice conversation, and control smart-home devices through the existing FastAPI command queue without breaking the current dashboard.

## Architecture Decision

- Keep the existing dashboard at `/` as the admin/debug surface.
- Add a new mobile app route at `/app` for the PWA home experience.
- Keep FastAPI as the API gateway for chat, voice, device commands, sensor data, PIR motion, and future database writes.
- Deploy frontend-only builds to Vercel later only if the API base URL can point to a public FastAPI backend.
- Use Supabase later for durable logs and state because Postgres fits command history, sensor readings, motion events, and report queries better than document-only storage.

## Safety Rules

- Do not rewrite the existing `webui/index.html`, `app_boot.js`, `app.js`, or dashboard flow during the first PWA phase.
- Do not send relay/device commands from the mobile UI while the ESP32 is offline unless the action is explicitly queued by the existing API.
- Keep every mobile action behind the existing backend APIs. The PWA must never try to call the ESP32 directly over LAN.
- Request microphone permission only after a user taps a voice control.
- Treat HTTPS as required for real phone microphone testing.

## Phase 1 - Mobile UI Shell

- [x] Add `/app` route that serves a separate mobile page.
- [x] Build a first-pass mobile home UI based on the reference: top bar, greeting hero, shortcuts, central voice button, device cards, recommendations, activity list, and bottom navigation.
- [x] Use mock-safe states when the board is unplugged.
- [x] Keep UI responsive for narrow and tall phone screens.
- [ ] Add more polished device detail views after the home shell is stable.
- [ ] Add real user avatar/profile settings.

## Phase 2 - PWA Installability

- [x] Add web app manifest.
- [x] Add service worker for app shell caching.
- [x] Add app icons and Apple touch icon.
- [x] Add manifest shortcuts for common actions: voice, dashboard, chat, devices.
- [ ] Verify install prompt on Android Chrome.
- [ ] Verify Add to Home Screen on iOS Safari.
- [ ] Add an in-app install/help panel only if users need guidance.

## Phase 3 - Phone Microphone

- [ ] Add explicit microphone permission panel.
- [ ] Use `navigator.mediaDevices.getUserMedia({ audio: true })` only after user tap.
- [ ] Record audio with `MediaRecorder`, choosing the best supported MIME type per browser.
- [ ] Upload audio to `/voice/chat` or `/assistant/audio`.
- [ ] Play TTS reply through the existing `/voice/audio/current` flow.
- [ ] Handle denied permission, insecure origin, missing MediaRecorder, timeout, and no-speech states.
- [ ] Test on Android Chrome over HTTPS.
- [ ] Test on iOS Safari/PWA over HTTPS.

## Phase 3A - Wake Word UX

- [x] Treat Wake Mode as a first-screen feature, not a hidden debug control.
- [x] Add a dedicated mobile Wake view with clear status and start/stop controls.
- [x] Add a first-screen Wake card that explains foreground listening.
- [x] Add PWA app shortcuts for Wake, Chat, Devices, and Status.
- [ ] Use browser `SpeechRecognition` for foreground wake listening when supported.
- [ ] Fall back to push-to-talk when browser wake listening is not supported.
- [ ] Keep ESP32 Voice Node wake listening as the preferred always-on path.
- [ ] Make the UI explain that a web PWA cannot listen from a closed/background app.

### Wake Word Reality Check

- Browser/PWA wake listening can only be reliable while the app page is open, foreground, and allowed to use the microphone.
- A service worker cannot access the DOM or microphone, so it cannot run an always-listening wake word loop after the PWA is closed.
- iOS/Android may pause page JavaScript and microphone capture when the app is backgrounded, locked, or killed.
- The robust "wake anytime" solution is the ESP32 Voice Node listening locally, then polling/reporting through the backend.
- The mobile PWA should therefore support two modes:
  - Phone Wake Mode: foreground wake listening after user starts it.
  - Board Wake Mode: command the ESP32 Voice Node to start wake listening when the voice board is online.

## Phase 3B - Mobile App Pages

- [x] Split mobile shell into Home, Wake, Chat, Devices, Status, and Settings views.
- [x] Keep navigation inside `/app` instead of sending users back to the desktop dashboard.
- [x] Reserve the old dashboard link for an explicit Admin Dashboard action.
- [x] Add polished chat history bubbles for the mobile Chat view.
- [x] Add command status steps for text chat and voice chat.
- [x] Show the latest voice command transcript after mobile STT returns.
- [ ] Add real-time backend progress events for STT, LLM, and TTS when the API is upgraded to streaming/jobs.
- [x] Add device detail screens for each relay/sensor/motion device.
- [x] Add settings permission diagnostics, install readiness, microphone test, and demo mode.
- [x] Add editable API target config for Vercel/mobile deployments.
- [x] Add browser install prompt handling and installed-app status.
- [x] Add local icon fallback so the PWA shell is not dependent on the CDN while offline.

## Phase 4 - Backend/Public Deploy

- [ ] Decide backend target: Render, Railway, Fly.io, Cloud Run, or local server via Cloudflare Tunnel for demo.
- [x] Add frontend runtime API base URL config for Vercel/static builds.
- [x] Add Vercel static routing for `/`, `/app`, manifest, service worker, and web assets.
- [x] Add `.vercelignore` so frontend deploys do not upload backend, firmware, reports, or local data.
- [ ] Keep ESP32 `SERVER_BASE_URL` pointed at the public FastAPI backend.
- [ ] Confirm ESP32 polling still uses `/esp32/commands`.
- [ ] Add CORS policy only for trusted frontend origins.
- [ ] Add request auth for deployed device endpoints before exposing to the public internet.

## Phase 5 - Supabase Database

- [x] Add SQL schema for `devices`.
- [x] Add SQL schema for `sensor_readings`.
- [x] Add SQL schema for `motion_events`.
- [x] Add SQL schema for `relay_commands`.
- [x] Add SQL schema for `command_results`.
- [x] Add SQL schema for `chat_messages`.
- [x] Add SQL schema for `voice_sessions`.
- [x] Add SQL schema for `system_logs`.
- [x] Add SQL schema for `activity_logs`.
- [x] Add seed data for the current ESP32 demo devices.
- [ ] Add repository/service layer in FastAPI so local in-memory managers can be migrated carefully.
- [x] Add migrations and seed data.

## Phase 6 - PIR Motion

- [ ] Keep PIR work planned separately until the board is connected.
- [ ] Confirm wiring: PIR OUT to configured GPIO, VCC, GND.
- [ ] Validate motion state changes in MicroPython logs.
- [ ] Confirm `POST /esp32/motion` receives real motion events.
- [ ] Store motion events in Supabase.
- [ ] Surface motion status and recent events in the mobile UI.

## Current First Step

Build the mobile/PWA shell and validate it locally without requiring the ESP32 board.
