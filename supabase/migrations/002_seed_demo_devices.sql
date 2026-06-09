-- Seed data matching the current local data/device_registry.json.

insert into public.board_devices (id, board_type, firmware_version, display_name)
values ('esp32-01', 'esp32-s3', null, 'Control Board')
on conflict (id) do update set
  board_type = excluded.board_type,
  display_name = excluded.display_name,
  updated_at = now();

insert into public.device_registry (
  id,
  display_name,
  device_type,
  room,
  esp32_device_id,
  gpio_pin,
  pin_mode,
  relay_channel,
  active_high,
  aliases,
  actions,
  enabled,
  is_user_defined
)
values
  (
    'relay_1',
    'ไฟห้องรับแขก',
    'relay',
    'ห้องรับแขก',
    'esp32-01',
    5,
    'output',
    1,
    true,
    '["ไฟ", "หลอดไฟ", "ไฟห้องรับแขก", "ไฟห้องนั่งเล่น", "ไฟรับแขก", "ห้องรับแขก", "living room light", "relay 1"]'::jsonb,
    '["on", "off"]'::jsonb,
    true,
    false
  ),
  (
    'relay_2',
    'ไฟห้องนอน',
    'relay',
    'ห้องนอน',
    'esp32-01',
    7,
    'output',
    2,
    true,
    '["ไฟห้องนอน", "หลอดไฟห้องนอน", "ห้องนอน", "bedroom light", "relay 2"]'::jsonb,
    '["on", "off"]'::jsonb,
    true,
    false
  ),
  (
    'relay_3',
    'ไฟห้องน้ำ',
    'relay',
    'ห้องน้ำ',
    'esp32-01',
    8,
    'output',
    3,
    true,
    '["ไฟห้องน้ำ", "หลอดไฟห้องน้ำ", "ห้องน้ำ", "bathroom light", "relay 3"]'::jsonb,
    '["on", "off"]'::jsonb,
    true,
    false
  ),
  (
    'relay_4',
    'ไฟห้องครัว',
    'relay',
    'ห้องครัว',
    'esp32-01',
    9,
    'output',
    4,
    true,
    '["ไฟห้องครัว", "หลอดไฟห้องครัว", "ห้องครัว", "kitchen light", "relay 4"]'::jsonb,
    '["on", "off"]'::jsonb,
    true,
    false
  ),
  (
    'dht22_1',
    'DHT22',
    'sensor',
    'demo',
    'esp32-01',
    4,
    'input',
    null,
    null,
    '["อุณหภูมิ", "ความชื้น", "เซนเซอร์", "dht22"]'::jsonb,
    '[]'::jsonb,
    true,
    false
  ),
  (
    'pir_1',
    'PIR Motion',
    'motion',
    'demo',
    'esp32-01',
    6,
    'input',
    null,
    null,
    '["pir", "motion", "การเคลื่อนไหว", "คนเดินผ่าน"]'::jsonb,
    '[]'::jsonb,
    true,
    false
  )
on conflict (id) do update set
  display_name = excluded.display_name,
  device_type = excluded.device_type,
  room = excluded.room,
  esp32_device_id = excluded.esp32_device_id,
  gpio_pin = excluded.gpio_pin,
  pin_mode = excluded.pin_mode,
  relay_channel = excluded.relay_channel,
  active_high = excluded.active_high,
  aliases = excluded.aliases,
  actions = excluded.actions,
  enabled = excluded.enabled,
  is_user_defined = excluded.is_user_defined,
  updated_at = now();
