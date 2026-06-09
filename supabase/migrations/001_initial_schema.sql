-- Nongfa AI Smart Home initial Supabase/Postgres schema.
-- Run this in Supabase SQL Editor or with psql against the target database.

create extension if not exists pgcrypto;

create table if not exists public.board_devices (
  id text primary key,
  board_type text not null default 'esp32-s3',
  firmware_version text,
  display_name text,
  last_seen_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.device_registry (
  id text primary key,
  display_name text not null,
  device_type text not null check (device_type in ('relay', 'sensor', 'motion', 'virtual')),
  room text,
  esp32_device_id text not null references public.board_devices(id) on update cascade on delete restrict,
  gpio_pin integer check (gpio_pin between 0 and 48),
  pin_mode text not null default 'virtual' check (pin_mode in ('input', 'output', 'i2s', 'virtual')),
  relay_channel integer check (relay_channel between 1 and 16),
  active_high boolean,
  aliases jsonb not null default '[]'::jsonb,
  actions jsonb not null default '[]'::jsonb,
  state text not null default 'unknown' check (state in ('unknown', 'on', 'off', 'pending', 'unavailable')),
  enabled boolean not null default true,
  is_user_defined boolean not null default false,
  last_command_id uuid,
  last_command_status text check (last_command_status in ('queued', 'sent', 'applied', 'failed', 'timeout')),
  last_updated_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.board_capabilities (
  id uuid primary key default gen_random_uuid(),
  device_id text not null references public.board_devices(id) on update cascade on delete cascade,
  board_type text not null,
  firmware_version text,
  capabilities jsonb not null default '[]'::jsonb,
  relay_pins jsonb not null default '[]'::jsonb,
  sensor_pins jsonb not null default '[]'::jsonb,
  reserved_pins jsonb not null default '[]'::jsonb,
  i2s_pins jsonb not null default '[]'::jsonb,
  available_pins jsonb not null default '[]'::jsonb,
  device_timestamp timestamptz not null,
  received_at timestamptz not null default now()
);

create table if not exists public.sensor_readings (
  id uuid primary key default gen_random_uuid(),
  device_id text not null references public.board_devices(id) on update cascade on delete cascade,
  temperature numeric(6,2) not null,
  humidity numeric(6,2) not null,
  device_timestamp timestamptz not null,
  received_at timestamptz not null default now()
);

create table if not exists public.motion_events (
  id uuid primary key default gen_random_uuid(),
  device_id text not null references public.board_devices(id) on update cascade on delete cascade,
  motion boolean not null,
  device_timestamp timestamptz not null,
  received_at timestamptz not null default now()
);

create table if not exists public.relay_commands (
  id uuid primary key default gen_random_uuid(),
  target_device_id text references public.device_registry(id) on update cascade on delete set null,
  esp32_device_id text not null references public.board_devices(id) on update cascade on delete restrict,
  relay_channel integer not null check (relay_channel between 1 and 16),
  gpio_pin integer check (gpio_pin between 0 and 48),
  action text not null check (action in ('on', 'off')),
  status text not null default 'queued' check (status in ('queued', 'sent', 'applied', 'failed', 'timeout')),
  source text not null default 'assistant',
  requested_text text,
  queued_at timestamptz not null default now(),
  sent_at timestamptz,
  applied_at timestamptz,
  failed_at timestamptz,
  error text
);

alter table public.device_registry
  drop constraint if exists device_registry_last_command_id_fkey;

alter table public.device_registry
  add constraint device_registry_last_command_id_fkey
  foreign key (last_command_id) references public.relay_commands(id)
  on update cascade on delete set null;

create table if not exists public.command_results (
  id uuid primary key default gen_random_uuid(),
  command_id uuid not null references public.relay_commands(id) on update cascade on delete cascade,
  esp32_device_id text not null references public.board_devices(id) on update cascade on delete restrict,
  status text not null check (status in ('applied', 'failed')),
  state text check (state in ('on', 'off')),
  error text,
  device_timestamp timestamptz not null,
  received_at timestamptz not null default now()
);

create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  session_id text not null default 'default',
  role text not null check (role in ('user', 'assistant', 'system')),
  content text not null,
  intent text,
  source text,
  audio_url text,
  created_at timestamptz not null default now()
);

create table if not exists public.voice_sessions (
  id uuid primary key default gen_random_uuid(),
  session_id text not null default 'default',
  heard_text text,
  reply text,
  intent text,
  source text,
  action text,
  keep_mic_open boolean not null default false,
  pir_state integer not null default 0 check (pir_state in (0, 1)),
  audio_url text,
  created_at timestamptz not null default now()
);

create table if not exists public.system_logs (
  id uuid primary key default gen_random_uuid(),
  level text not null default 'info' check (level in ('debug', 'info', 'warn', 'error')),
  component text not null,
  message text not null,
  context jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.activity_logs (
  id uuid primary key default gen_random_uuid(),
  activity_type text not null,
  title text not null,
  detail text,
  device_id text,
  command_id uuid references public.relay_commands(id) on update cascade on delete set null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_device_registry_esp32_device_id on public.device_registry(esp32_device_id);
create index if not exists idx_sensor_readings_device_time on public.sensor_readings(device_id, received_at desc);
create index if not exists idx_motion_events_device_time on public.motion_events(device_id, received_at desc);
create index if not exists idx_motion_events_detected_time on public.motion_events(received_at desc) where motion = true;
create index if not exists idx_relay_commands_device_status on public.relay_commands(esp32_device_id, status, queued_at);
create index if not exists idx_command_results_command on public.command_results(command_id, received_at desc);
create index if not exists idx_chat_messages_session_time on public.chat_messages(session_id, created_at);
create index if not exists idx_voice_sessions_time on public.voice_sessions(created_at desc);
create index if not exists idx_system_logs_time on public.system_logs(created_at desc);
create index if not exists idx_activity_logs_time on public.activity_logs(created_at desc);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_board_devices_updated_at on public.board_devices;
create trigger trg_board_devices_updated_at
before update on public.board_devices
for each row execute function public.set_updated_at();

drop trigger if exists trg_device_registry_updated_at on public.device_registry;
create trigger trg_device_registry_updated_at
before update on public.device_registry
for each row execute function public.set_updated_at();

alter table public.board_devices enable row level security;
alter table public.device_registry enable row level security;
alter table public.board_capabilities enable row level security;
alter table public.sensor_readings enable row level security;
alter table public.motion_events enable row level security;
alter table public.relay_commands enable row level security;
alter table public.command_results enable row level security;
alter table public.chat_messages enable row level security;
alter table public.voice_sessions enable row level security;
alter table public.system_logs enable row level security;
alter table public.activity_logs enable row level security;

comment on table public.device_registry is 'Smart-home devices known by Nongfa. Keep anon access disabled unless explicit RLS policies are added.';
comment on table public.sensor_readings is 'DHT22 or environmental readings reported by ESP32 boards.';
comment on table public.motion_events is 'PIR motion events reported by ESP32 boards.';
comment on table public.relay_commands is 'Relay commands queued by AI/chat/device UI and consumed by ESP32 polling.';
comment on table public.command_results is 'ESP32 confirmations for relay commands.';
comment on table public.chat_messages is 'Text chat log for user and assistant turns.';
comment on table public.voice_sessions is 'Mobile/voice-node conversation turns including STT transcript and TTS audio URL.';
