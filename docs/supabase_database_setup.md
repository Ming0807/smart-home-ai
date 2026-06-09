# Supabase Database Setup

This project can keep running with the current local JSON/in-memory managers while the database is being prepared. The Supabase schema below is the target storage layer for the teacher requirement: devices, sensor logs, motion logs, relay commands, command results, chat logs, voice logs, activity logs, and system logs.

## Recommended Order

1. Create a Supabase project.
2. Open the SQL Editor.
3. Run `supabase/migrations/001_initial_schema.sql`.
4. Run `supabase/migrations/002_seed_demo_devices.sql`.
5. Keep Row Level Security enabled. Do not add public anon policies for device command tables.
6. Configure backend environment variables only after the schema exists.

## Backend Environment

Set these values in the backend host when database integration is enabled:

```env
DATABASE_ENABLED=true
DATABASE_URL=postgresql+psycopg://postgres:<password>@<host>:5432/postgres
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<anon-key>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
```

For local development, leave `DATABASE_ENABLED=false` or unset. The existing local managers continue to work.

## What The Tables Store

- `board_devices`: ESP32 boards and last heartbeat metadata.
- `device_registry`: Relay, sensor, motion, and virtual device definitions.
- `board_capabilities`: ESP32 pin/capability reports from `send_capabilities`.
- `sensor_readings`: DHT22 temperature and humidity readings.
- `motion_events`: PIR motion events.
- `relay_commands`: Commands queued by AI/chat/device UI for ESP32 polling.
- `command_results`: ESP32 command confirmations.
- `chat_messages`: Text chat turns and response metadata.
- `voice_sessions`: STT transcript, AI reply, action, and TTS URL for voice turns.
- `system_logs`: Backend/system diagnostics.
- `activity_logs`: User-facing activity feed events.

## Current Integration State

The schema is ready, but the FastAPI services still use the existing local storage path by default. This is intentional: it keeps the board demo stable while the database is introduced carefully.

Next implementation step:

1. Add a database repository layer.
2. Mirror incoming ESP32 sensor/motion/command result events into Supabase.
3. Mirror chat and voice turns into Supabase.
4. Move device registry reads/writes from JSON to Supabase when `DATABASE_ENABLED=true`.
5. Keep local JSON/in-memory fallback for demos without internet.

## Security Notes

- Keep `SUPABASE_SERVICE_ROLE_KEY` only on the backend. Never expose it in the PWA.
- The mobile PWA should use the FastAPI backend, not Supabase directly, for command writes.
- Use authenticated backend endpoints before exposing ESP32 command polling publicly.
- RLS is enabled in the migration without public policies, so anon browser access is not granted by default.
