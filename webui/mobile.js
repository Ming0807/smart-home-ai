const RECORDING_MAX_MS = 9000;
const RECORDING_MIN_MS = 900;
const RECORDING_SILENCE_STOP_MS = 1200;
const RECORDING_NO_SPEECH_STOP_MS = 4500;
const RECORDING_RMS_THRESHOLD = 0.035;
const BROWSER_SPEECH_LISTEN_MAX_MS = 30000;
const BROWSER_SPEECH_RESTART_GRACE_MS = 600;
const VOICE_CONTINUE_DELAY_MS = 1400;
const REPLY_AUDIO_READY_TIMEOUT_MS = 12000;
const REPLY_AUDIO_STATUS_POLL_MS = 750;
const SpeechRecognitionConstructor =
  window.SpeechRecognition || window.webkitSpeechRecognition || null;
const WAKE_WORDS = ["น้องฟ้า", "นองฟ้า", "nong fa", "nongfa"];
const VOICE_CONVERSATION_END_WORDS = [
  "ขอบคุณ",
  "พอแล้ว",
  "หยุดฟัง",
  "เลิกฟัง",
  "เลิกคุย",
  "ปิดการฟัง",
  "ไม่ต้องฟังต่อ",
  "thankyou",
  "stoplistening",
];
const CHAT_STEPS = [
  { id: "input", label: "รับคำสั่ง" },
  { id: "audio", label: "บันทึกเสียง" },
  { id: "upload", label: "ส่งข้อมูล" },
  { id: "stt", label: "แปลงเสียง" },
  { id: "thinking", label: "AI คิด" },
  { id: "reply", label: "ตอบกลับ" },
];
const DEMO_MODE_STORAGE_KEY = "nongfa.mobile.demoMode";
const API_BASE_STORAGE_KEY = "nongfa.mobile.apiBase";
const DEFAULT_API_BASE = window.NONGFA_API_BASE || "";
const DEMO_DASHBOARD_SNAPSHOT = {
  llm: { available: true },
  device: {
    online: true,
    latest_command: { action: "on", channel: 1 },
  },
  sensor: {
    temperature: 28.3,
    humidity: 62,
    is_fresh: true,
    received_at: new Date().toISOString(),
  },
  motion: {
    motion_detected: false,
    last_motion_at: null,
  },
};
const DEMO_DEVICES = [
  {
    id: "relay_1",
    display_name: "ไฟห้องรับแขก",
    device_type: "relay",
    room: "ห้องรับแขก",
    esp32_device_id: "esp32-01",
    gpio_pin: 5,
    pin_mode: "output",
    relay_channel: 1,
    active_high: true,
    aliases: ["ไฟ", "ไฟห้องรับแขก", "ไฟห้องนั่งเล่น"],
    actions: ["on", "off"],
    state: "on",
    enabled: true,
    last_command_status: "applied",
    last_updated_at: new Date().toISOString(),
  },
  {
    id: "relay_2",
    display_name: "ไฟห้องนอน",
    device_type: "relay",
    room: "ห้องนอน",
    esp32_device_id: "esp32-01",
    gpio_pin: 7,
    pin_mode: "output",
    relay_channel: 2,
    active_high: true,
    aliases: ["ไฟห้องนอน", "bedroom light"],
    actions: ["on", "off"],
    state: "off",
    enabled: true,
    last_command_status: "applied",
    last_updated_at: new Date().toISOString(),
  },
  {
    id: "relay_3",
    display_name: "ไฟห้องน้ำ",
    device_type: "relay",
    room: "ห้องน้ำ",
    esp32_device_id: "esp32-01",
    gpio_pin: 8,
    pin_mode: "output",
    relay_channel: 3,
    active_high: true,
    aliases: ["ไฟห้องน้ำ", "bathroom light"],
    actions: ["on", "off"],
    state: "off",
    enabled: true,
    last_command_status: "applied",
    last_updated_at: new Date().toISOString(),
  },
  {
    id: "relay_4",
    display_name: "ไฟห้องครัว",
    device_type: "relay",
    room: "ห้องครัว",
    esp32_device_id: "esp32-01",
    gpio_pin: 9,
    pin_mode: "output",
    relay_channel: 4,
    active_high: true,
    aliases: ["ไฟห้องครัว", "kitchen light"],
    actions: ["on", "off"],
    state: "off",
    enabled: true,
    last_command_status: "applied",
    last_updated_at: new Date().toISOString(),
  },
  {
    id: "dht22_1",
    display_name: "DHT22",
    device_type: "sensor",
    room: "demo",
    esp32_device_id: "esp32-01",
    gpio_pin: 4,
    pin_mode: "input",
    aliases: ["อุณหภูมิ", "ความชื้น", "dht22"],
    actions: [],
    state: "unknown",
    enabled: true,
  },
  {
    id: "pir_1",
    display_name: "PIR Motion",
    device_type: "motion",
    room: "demo",
    esp32_device_id: "esp32-01",
    gpio_pin: 6,
    pin_mode: "input",
    aliases: ["pir", "motion", "การเคลื่อนไหว"],
    actions: [],
    state: "unknown",
    enabled: true,
  },
];
const DEMO_DEVICE_STATUS = {
  devices: DEMO_DEVICES,
  total: DEMO_DEVICES.length,
  enabled: DEMO_DEVICES.filter((device) => device.enabled).length,
};

let apiBase = getInitialApiBase();

const els = {
  heroTemperature: document.getElementById("hero-temperature"),
  heroHumidity: document.getElementById("hero-humidity"),
  heroAir: document.getElementById("hero-air"),
  temperatureCard: document.getElementById("temperature-card"),
  humidityCard: document.getElementById("humidity-card"),
  lightState: document.getElementById("light-state"),
  lightToggle: document.getElementById("light-toggle"),
  voiceOrb: document.getElementById("voice-orb"),
  navVoice: document.getElementById("nav-voice"),
  statusShortcut: document.getElementById("status-shortcut"),
  settingsShortcut: document.getElementById("settings-shortcut"),
  voiceStatus: document.getElementById("voice-status"),
  wakeSummaryStatus: document.getElementById("wake-summary-status"),
  phoneWakeStatus: document.getElementById("phone-wake-status"),
  boardWakeStatus: document.getElementById("board-wake-status"),
  phoneWakeStart: document.getElementById("phone-wake-start"),
  phoneWakeStop: document.getElementById("phone-wake-stop"),
  boardWakeStart: document.getElementById("board-wake-start"),
  boardWakeStop: document.getElementById("board-wake-stop"),
  chatForm: document.getElementById("mobile-chat-form"),
  chatInput: document.getElementById("mobile-chat-input"),
  chatSubmit: document.getElementById("mobile-chat-submit"),
  chatReply: document.getElementById("mobile-chat-reply"),
  chatHistory: document.getElementById("mobile-chat-history"),
  chatStatus: document.getElementById("mobile-chat-status"),
  chatStatusLabel: document.getElementById("mobile-chat-status-label"),
  chatStatusTitle: document.getElementById("mobile-chat-status-title"),
  chatStatusDetail: document.getElementById("mobile-chat-status-detail"),
  chatSteps: document.getElementById("mobile-chat-steps"),
  voiceTranscriptPanel: document.getElementById("mobile-voice-transcript-panel"),
  voiceTranscript: document.getElementById("mobile-voice-transcript"),
  activityCommand: document.getElementById("activity-command"),
  activityCommandMeta: document.getElementById("activity-command-meta"),
  activityCommandTime: document.getElementById("activity-command-time"),
  activitySensor: document.getElementById("activity-sensor"),
  activitySensorTime: document.getElementById("activity-sensor-time"),
  devicesSummary: document.getElementById("devices-summary"),
  mobileDeviceList: document.getElementById("mobile-device-list"),
  deviceDetailBack: document.getElementById("device-detail-back"),
  deviceDetailType: document.getElementById("device-detail-type"),
  deviceDetailTitle: document.getElementById("device-detail-title"),
  deviceDetailSummary: document.getElementById("device-detail-summary"),
  deviceDetailIcon: document.getElementById("device-detail-icon"),
  deviceDetailStateBadge: document.getElementById("device-detail-state-badge"),
  deviceDetailState: document.getElementById("device-detail-state"),
  deviceDetailLast: document.getElementById("device-detail-last"),
  deviceDetailRoom: document.getElementById("device-detail-room"),
  deviceDetailGpio: document.getElementById("device-detail-gpio"),
  deviceDetailBoard: document.getElementById("device-detail-board"),
  deviceDetailChannel: document.getElementById("device-detail-channel"),
  deviceDetailStateMeta: document.getElementById("device-detail-state-meta"),
  deviceDetailCommand: document.getElementById("device-detail-command"),
  deviceActionOn: document.getElementById("device-action-on"),
  deviceActionOff: document.getElementById("device-action-off"),
  deviceActionQuery: document.getElementById("device-action-query"),
  deviceDetailActionStatus: document.getElementById("device-detail-action-status"),
  deviceDetailAliases: document.getElementById("device-detail-aliases"),
  statusAi: document.getElementById("status-ai"),
  statusControlBoard: document.getElementById("status-control-board"),
  statusVoiceBoard: document.getElementById("status-voice-board"),
  statusDevices: document.getElementById("status-devices"),
  statusWakeDetail: document.getElementById("status-wake-detail"),
  statusRefreshTime: document.getElementById("status-refresh-time"),
  statusSensorDetail: document.getElementById("status-sensor-detail"),
  statusSensorTime: document.getElementById("status-sensor-time"),
  settingsMicTest: document.getElementById("settings-test-mic"),
  settingsMicTestStatus: document.getElementById("settings-mic-test-status"),
  settingsInstallApp: document.getElementById("settings-install-app"),
  settingsInstallStatus: document.getElementById("settings-install-status"),
  settingsDemoToggle: document.getElementById("settings-demo-toggle"),
  settingsDemoStatus: document.getElementById("settings-demo-status"),
  settingsApiForm: document.getElementById("settings-api-form"),
  settingsApiBaseInput: document.getElementById("settings-api-base-input"),
  settingsApiBaseCurrent: document.getElementById("settings-api-base-current"),
  settingsApiBaseStatus: document.getElementById("settings-api-base-status"),
  settingsApiTest: document.getElementById("settings-api-test"),
  settingsApiReset: document.getElementById("settings-api-reset"),
  settingsRefreshDiagnostics: document.getElementById("settings-refresh-diagnostics"),
  diagSecure: document.getElementById("diag-secure"),
  diagMic: document.getElementById("diag-mic"),
  diagSpeech: document.getElementById("diag-speech"),
  diagServiceWorker: document.getElementById("diag-service-worker"),
  diagPwa: document.getElementById("diag-pwa"),
  diagApi: document.getElementById("diag-api"),
};

const state = {
  currentView: "home",
  deviceOnline: false,
  lightOn: false,
  phoneWakeListening: false,
  wakeRecognition: null,
  voiceRecognition: null,
  voiceRecognitionTimeout: 0,
  voiceTurnId: 0,
  dashboardSnapshot: null,
  voiceNodeStatus: null,
  deviceRegistryStatus: null,
  mediaRecorder: null,
  mediaStream: null,
  audioContext: null,
  analyser: null,
  voiceVadTimer: 0,
  voiceRecordingStartedAt: 0,
  voiceLastSpeechAt: 0,
  voiceSpeechStarted: false,
  voiceConversationMode: false,
  voiceResumeWakeAfterTurn: false,
  audioChunks: [],
  recordingTimeout: 0,
  voiceContinueTimer: 0,
  chatBusy: false,
  voiceBusy: false,
  chatStatusTimers: [],
  selectedDeviceId: null,
  demoMode: readStorage(DEMO_MODE_STORAGE_KEY) === "1",
  deferredInstallPrompt: null,
  appInstalled: false,
};

function readStorage(key) {
  try {
    return window.localStorage?.getItem(key) || "";
  } catch (error) {
    return "";
  }
}

function writeStorage(key, value) {
  try {
    if (value) {
      window.localStorage?.setItem(key, value);
    } else {
      window.localStorage?.removeItem(key);
    }
  } catch (error) {
    // Ignore storage errors in restricted browser modes.
  }
}

function normalizeApiBase(value) {
  const rawValue = String(value || "").trim().replace(/\/+$/, "");
  if (!rawValue) {
    return "";
  }
  try {
    const url = new URL(rawValue);
    if (url.protocol === "https:" || url.protocol === "http:") {
      return url.origin === window.location.origin ? "" : url.origin;
    }
  } catch (error) {
    return "";
  }
  return "";
}

function getInitialApiBase() {
  const params = new URLSearchParams(window.location.search);
  const queryApiBase = normalizeApiBase(params.get("apiBase") || params.get("api_base") || "");
  if (queryApiBase) {
    writeStorage(API_BASE_STORAGE_KEY, queryApiBase);
    return queryApiBase;
  }
  return normalizeApiBase(readStorage(API_BASE_STORAGE_KEY) || DEFAULT_API_BASE);
}

function apiBaseLabel() {
  return apiBase || "same-origin";
}

function apiUrl(path) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${apiBase}${normalizedPath}`;
}

async function fetchJson(path, options = {}, timeoutMs = 30000) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(apiUrl(path), {
      ...options,
      signal: controller.signal,
      cache: "no-store",
    });
    const text = await response.text();
    const data = text ? JSON.parse(text) : {};
    return { response, data };
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function setText(element, value) {
  if (element) {
    element.textContent = value;
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "--";
  }
  return `${Math.round(Number(value))}%`;
}

function formatTemperature(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "--";
  }
  return `${Number(value).toFixed(1)}°C`;
}

function formatTime(value) {
  if (!value) {
    return "--:--";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "--:--";
  }
  return new Intl.DateTimeFormat("th-TH", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function mobileVoiceNodeStateLabel(stateValue) {
  const value = String(stateValue || "");
  const labels = {
    BOOT: "กำลังเริ่มระบบ",
    WIFI_CONNECTING: "กำลังต่อ Wi-Fi",
    REGISTERING: "กำลังลงทะเบียน",
    WAKE_LISTENING: "รอฟังคำปลุก",
    WAKE_DETECTED: "ได้ยินคำปลุก",
    BEEPING: "กำลังส่งเสียงติ๊ด",
    RECORDING_COMMAND: "กำลังฟังประโยค",
    UPLOADING_AUDIO: "กำลังส่งเสียง",
    WAITING_SERVER_REPLY: "AI กำลังตอบ",
    PLAYING_REPLY: "กำลังเล่นเสียง",
    COOLDOWN: "พักรอบสนทนา",
    ERROR: "บอร์ดมีปัญหา",
  };
  return labels[value] || value || "online";
}

function mobileVoiceNodeWakeStatus(nodeStatus) {
  if (!nodeStatus?.online) {
    return "ยังไม่พบ voice node";
  }
  if (!nodeStatus.wake_mode_enabled) {
    return "บอร์ดยังไม่ได้เปิด wake";
  }
  return nodeStatus.wake_conversation_active
    ? "บอร์ดคุยอยู่หลังคำปลุก"
    : "บอร์ดรอฟังคำว่า น้องฟ้า";
}

function setVoiceStatus(message, tone = "neutral") {
  setText(els.voiceStatus, message);
  els.voiceStatus?.setAttribute("data-tone", tone);
}

function clearChatStatusTimers() {
  for (const timer of state.chatStatusTimers) {
    window.clearTimeout(timer);
  }
  state.chatStatusTimers = [];
}

function renderChatSteps(activeStep = "input", completedSteps = []) {
  if (!els.chatSteps) {
    return;
  }
  const completed = new Set(completedSteps);
  els.chatSteps.innerHTML = "";

  for (const step of CHAT_STEPS) {
    const item = document.createElement("span");
    item.className = "chat-step";
    if (completed.has(step.id)) {
      item.classList.add("done");
    }
    if (step.id === activeStep) {
      item.classList.add("active");
    }
    item.textContent = step.label;
    els.chatSteps.appendChild(item);
  }
}

function updateChatStatus({
  title,
  detail = "",
  label = "",
  tone = "neutral",
  activeStep = "input",
  completedSteps = [],
  mirrorToFooter = true,
}) {
  setText(els.chatStatusTitle, title);
  setText(els.chatStatusDetail, detail);
  setText(els.chatStatusLabel, label || title);
  els.chatStatus?.setAttribute("data-tone", tone);
  renderChatSteps(activeStep, completedSteps);
  if (mirrorToFooter) {
    setText(els.chatReply, detail || title);
  }
}

function queueChatStatus(delayMs, status) {
  const timer = window.setTimeout(() => updateChatStatus(status), delayMs);
  state.chatStatusTimers.push(timer);
}

function setChatBusy(isBusy) {
  state.chatBusy = isBusy;
  if (els.chatSubmit) {
    els.chatSubmit.disabled = isBusy;
  }
  els.chatForm?.setAttribute("aria-busy", String(isBusy));
}

function setVoiceTranscript(text, tone = "neutral") {
  setText(els.voiceTranscript, text || "ยังไม่มีคำสั่งเสียง");
  els.voiceTranscriptPanel?.setAttribute("data-tone", tone);
}

function activeViewFromHash() {
  const hash = (window.location.hash || "#home").replace("#", "").trim();
  if (hash.startsWith("device:")) {
    state.selectedDeviceId = decodeURIComponent(hash.slice("device:".length));
    return "device-detail";
  }
  if (["home", "wake", "chat", "devices", "status", "settings"].includes(hash)) {
    state.selectedDeviceId = null;
    return hash;
  }
  state.selectedDeviceId = null;
  return "home";
}

function setActiveView(viewName) {
  state.currentView = viewName;
  document.querySelectorAll(".app-view").forEach((view) => {
    view.classList.toggle("active", view.dataset.view === viewName);
  });
  document.querySelectorAll(".bottom-nav a").forEach((item) => {
    const target = (item.getAttribute("href") || "").replace("#", "");
    item.classList.toggle("active", target === viewName || (viewName === "device-detail" && target === "devices"));
  });
}

function routeFromLocation() {
  const viewName = activeViewFromHash();
  setActiveView(viewName);
  if (viewName === "device-detail") {
    renderSelectedDeviceDetail();
  }
  if (viewName === "settings") {
    updateSettingsUi();
    void refreshDiagnostics();
  }
  window.scrollTo(0, 0);
}

function normalizeWakeText(text) {
  return String(text || "").toLocaleLowerCase().replace(/\s+/g, "");
}

function detectWakeWord(text) {
  const normalized = normalizeWakeText(text);
  return WAKE_WORDS.some((word) => normalized.includes(normalizeWakeText(word)));
}

function shouldEndVoiceConversation(text) {
  const normalized = normalizeWakeText(text);
  return VOICE_CONVERSATION_END_WORDS.some((word) => normalized.includes(normalizeWakeText(word)));
}

function collectSpeechText(event) {
  const parts = [];
  for (let index = event.resultIndex || 0; index < event.results.length; index += 1) {
    const transcript = event.results[index]?.[0]?.transcript;
    if (transcript) {
      parts.push(transcript);
    }
  }
  return parts.join(" ").trim();
}

function appendChatBubble(role, text) {
  if (!els.chatHistory || !text) {
    return;
  }
  const bubble = document.createElement("article");
  bubble.className = `chat-bubble ${role === "user" ? "user" : "assistant"}`;
  bubble.textContent = text;
  els.chatHistory.appendChild(bubble);
  if (els.chatHistory.childElementCount > 24) {
    els.chatHistory.firstElementChild?.remove();
  }
}

function setLightUi(on, online) {
  state.lightOn = Boolean(on);
  els.lightToggle?.classList.toggle("is-on", state.lightOn);
  els.lightToggle?.toggleAttribute("disabled", !online);

  if (!online) {
    setText(els.lightState, "บอร์ด offline");
    return;
  }
  setText(els.lightState, state.lightOn ? "เปิดอยู่" : "ปิดอยู่");
}

function updateDashboardUi(snapshot) {
  state.dashboardSnapshot = snapshot;
  const sensor = snapshot?.sensor || {};
  const device = snapshot?.device || {};
  const command = device.latest_command || null;
  const temperature = formatTemperature(sensor.temperature);
  const humidity = formatPercent(sensor.humidity);

  state.deviceOnline = Boolean(device.online);
  setText(els.heroTemperature, temperature);
  setText(els.heroHumidity, humidity);
  setText(els.temperatureCard, temperature);
  setText(els.humidityCard, humidity);
  setText(els.heroAir, sensor.is_fresh ? "อากาศดี" : "รอเซ็นเซอร์");
  setLightUi(command?.action === "on", state.deviceOnline);

  if (command) {
    const actionLabel = command.action === "on" ? "เปิดไฟ" : "ปิดไฟ";
    setText(els.activityCommand, actionLabel);
    setText(els.activityCommandMeta, `relay channel ${command.channel || 1}`);
    setText(els.activityCommandTime, "ล่าสุด");
  } else {
    setText(els.activityCommand, state.deviceOnline ? "บอร์ดพร้อมรับคำสั่ง" : "ยังไม่มีคำสั่งล่าสุด");
    setText(els.activityCommandMeta, state.deviceOnline ? "ESP32 online" : "รอการเชื่อมต่อบอร์ด");
    setText(els.activityCommandTime, "--:--");
  }

  if (sensor.received_at) {
    setText(els.activitySensor, `${temperature} • ${humidity}`);
    setText(els.activitySensorTime, formatTime(sensor.received_at));
  } else {
    setText(els.activitySensor, "ยังไม่มีข้อมูลเซ็นเซอร์");
    setText(els.activitySensorTime, "--:--");
  }

  setText(els.statusAi, snapshot?.llm?.available ? "พร้อมใช้งาน" : "รอตรวจสอบ");
  setText(els.statusControlBoard, device.online ? "online" : "offline");
  setText(els.statusSensorDetail, sensor.received_at ? `${temperature} • ${humidity}` : "ยังไม่มีข้อมูล");
  setText(els.statusSensorTime, formatTime(sensor.received_at));
  setText(els.statusRefreshTime, formatTime(new Date().toISOString()));
}

async function refreshDashboardStatus() {
  if (state.demoMode) {
    updateDashboardUi({
      ...DEMO_DASHBOARD_SNAPSHOT,
      sensor: {
        ...DEMO_DASHBOARD_SNAPSHOT.sensor,
        received_at: new Date().toISOString(),
      },
    });
    return;
  }

  try {
    const { response, data } = await fetchJson("/dashboard/status", {}, 10000);
    if (!response.ok) {
      throw new Error("dashboard status failed");
    }
    updateDashboardUi(data);
  } catch (error) {
    state.deviceOnline = false;
    setLightUi(false, false);
    setText(els.heroAir, "เชื่อมต่อ server ไม่ได้");
  }
}

async function refreshVoiceNodeStatus() {
  if (state.demoMode) {
    state.voiceNodeStatus = {
      online: true,
      state: "demo",
      wake_mode_enabled: false,
    };
    setText(els.statusVoiceBoard, "demo");
    setText(els.boardWakeStatus, "โหมดเดโมยังไม่สั่งบอร์ดจริง");
    setText(els.statusWakeDetail, state.phoneWakeListening ? "มือถือกำลังรอคำว่า น้องฟ้า" : "Demo Mode พร้อม");
    return;
  }

  try {
    const { response, data } = await fetchJson("/voice-node/status?device_id=voice-node-01", {}, 8000);
    if (!response.ok) {
      throw new Error("voice node status failed");
    }
    state.voiceNodeStatus = data;
    const boardStatus = data.online ? mobileVoiceNodeStateLabel(data.state) : "offline";
    const wakeStatus = mobileVoiceNodeWakeStatus(data);
    setText(els.statusVoiceBoard, boardStatus);
    setText(els.boardWakeStatus, wakeStatus);
    setText(
      els.statusWakeDetail,
      state.phoneWakeListening
        ? "มือถือกำลังรอคำว่า น้องฟ้า"
        : data.wake_mode_enabled
          ? `${wakeStatus} • ${boardStatus}`
          : "ยังไม่ได้เปิด Wake Mode"
    );
  } catch (error) {
    state.voiceNodeStatus = null;
    setText(els.statusVoiceBoard, "offline");
    setText(els.boardWakeStatus, "ยังไม่พบ voice node");
  }
}

function deviceIconName(deviceType) {
  if (deviceType === "relay") {
    return "lightbulb";
  }
  if (deviceType === "sensor") {
    return "thermometer";
  }
  if (deviceType === "motion") {
    return "radar";
  }
  return "plug";
}

function deviceTypeLabel(deviceType) {
  if (deviceType === "relay") {
    return "Relay";
  }
  if (deviceType === "sensor") {
    return "Sensor";
  }
  if (deviceType === "motion") {
    return "PIR Motion";
  }
  return "Virtual";
}

function deviceStateLabel(stateValue) {
  const value = String(stateValue || "unknown");
  if (value === "on") {
    return "เปิดอยู่";
  }
  if (value === "off") {
    return "ปิดอยู่";
  }
  if (value === "pending") {
    return "รอยืนยัน";
  }
  if (value === "unavailable") {
    return "ไม่พร้อม";
  }
  return "ยังไม่ทราบ";
}

function commandStatusLabel(statusValue) {
  const value = String(statusValue || "");
  if (value === "queued") {
    return "รอส่ง";
  }
  if (value === "sent") {
    return "ส่งแล้ว";
  }
  if (value === "applied") {
    return "ยืนยันแล้ว";
  }
  if (value === "failed") {
    return "ล้มเหลว";
  }
  if (value === "timeout") {
    return "หมดเวลา";
  }
  return "--";
}

function currentDevices() {
  return Array.isArray(state.deviceRegistryStatus?.devices) ? state.deviceRegistryStatus.devices : [];
}

function findDeviceById(deviceId) {
  return currentDevices().find((device) => device.id === deviceId) || null;
}

function deviceDetailSummary(device) {
  const parts = [
    device.room || "ไม่ระบุห้อง",
    device.gpio_pin !== null && device.gpio_pin !== undefined ? `GPIO ${device.gpio_pin}` : null,
    device.relay_channel ? `CH ${device.relay_channel}` : null,
  ].filter(Boolean);
  return parts.join(" • ") || deviceTypeLabel(device.device_type);
}

function deviceLastDetail(device) {
  if (device.device_type === "sensor") {
    const sensor = state.dashboardSnapshot?.sensor || {};
    const temperature = formatTemperature(sensor.temperature);
    const humidity = formatPercent(sensor.humidity);
    return sensor.received_at ? `${temperature} • ${humidity} • ${formatTime(sensor.received_at)}` : "รอข้อมูลจาก DHT22";
  }
  if (device.device_type === "motion") {
    const motion = state.dashboardSnapshot?.motion || {};
    if (motion.last_motion_at) {
      return `พบ motion ล่าสุด ${formatTime(motion.last_motion_at)}`;
    }
    return motion.motion_detected ? "กำลังพบการเคลื่อนไหว" : "ยังไม่มี motion ล่าสุด";
  }
  if (device.last_updated_at) {
    return `อัปเดตล่าสุด ${formatTime(device.last_updated_at)}`;
  }
  return state.deviceOnline ? "บอร์ดพร้อมรับคำสั่ง" : "บอร์ดยัง offline";
}

function renderDeviceAliases(device) {
  if (!els.deviceDetailAliases) {
    return;
  }
  els.deviceDetailAliases.innerHTML = "";
  const aliases = Array.isArray(device.aliases) ? device.aliases : [];
  if (!aliases.length) {
    const empty = document.createElement("span");
    empty.textContent = "ยังไม่มี alias";
    els.deviceDetailAliases.appendChild(empty);
    return;
  }
  for (const alias of aliases.slice(0, 10)) {
    const item = document.createElement("span");
    item.textContent = alias;
    els.deviceDetailAliases.appendChild(item);
  }
}

function renderSelectedDeviceDetail() {
  const device = findDeviceById(state.selectedDeviceId);
  if (!device) {
    setText(els.deviceDetailType, "Device");
    setText(els.deviceDetailTitle, "ไม่พบอุปกรณ์");
    setText(els.deviceDetailSummary, "กลับไปหน้าอุปกรณ์เพื่อเลือกใหม่");
    setText(els.deviceDetailStateBadge, "missing");
    setText(els.deviceDetailState, "ไม่มีข้อมูล");
    setText(els.deviceDetailLast, "--");
    setText(els.deviceDetailActionStatus, "โหลดข้อมูลอุปกรณ์ไม่สำเร็จ");
    els.deviceActionOn?.setAttribute("hidden", "");
    els.deviceActionOff?.setAttribute("hidden", "");
    els.deviceActionQuery?.setAttribute("hidden", "");
    return;
  }

  const stateLabel = deviceStateLabel(device.state);
  const commandLabel = commandStatusLabel(device.last_command_status);
  const isRelay = device.device_type === "relay";
  const isEnabled = Boolean(device.enabled);
  const iconName = deviceIconName(device.device_type);

  setText(els.deviceDetailType, deviceTypeLabel(device.device_type));
  setText(els.deviceDetailTitle, device.display_name || device.id);
  setText(els.deviceDetailSummary, deviceDetailSummary(device));
  setText(els.deviceDetailStateBadge, isEnabled ? "เปิดใช้" : "ปิดใช้งาน");
  els.deviceDetailStateBadge?.classList.toggle("enabled", isEnabled);
  setText(els.deviceDetailState, stateLabel);
  setText(els.deviceDetailLast, deviceLastDetail(device));
  setText(els.deviceDetailRoom, device.room || "--");
  setText(els.deviceDetailGpio, device.gpio_pin !== null && device.gpio_pin !== undefined ? `GPIO ${device.gpio_pin}` : "--");
  setText(els.deviceDetailBoard, device.esp32_device_id || "--");
  setText(els.deviceDetailChannel, device.relay_channel ? `CH ${device.relay_channel}` : "--");
  setText(els.deviceDetailStateMeta, stateLabel);
  setText(els.deviceDetailCommand, commandLabel);
  setText(els.deviceDetailActionStatus, isRelay ? "เลือกเปิดหรือปิดผ่าน AI command" : "ใช้อ่านสถานะผ่าน AI command");
  els.deviceDetailIcon?.setAttribute("data-lucide", iconName);
  els.deviceActionOn?.toggleAttribute("hidden", !isRelay);
  els.deviceActionOff?.toggleAttribute("hidden", !isRelay);
  els.deviceActionQuery?.toggleAttribute("hidden", false);
  renderDeviceAliases(device);
  window.lucide?.createIcons();
}

function deviceQueryText(device) {
  if (device.device_type === "sensor") {
    return "อ่านค่าอุณหภูมิและความชื้น";
  }
  if (device.device_type === "motion") {
    return "motion ล่าสุดเมื่อไหร่";
  }
  return `สถานะ${device.display_name || device.id}`;
}

async function runSelectedDeviceAction(action) {
  const device = findDeviceById(state.selectedDeviceId);
  if (!device) {
    setText(els.deviceDetailActionStatus, "ไม่พบอุปกรณ์ที่เลือก");
    return;
  }

  const commandText = action === "query"
    ? deviceQueryText(device)
    : `${action === "on" ? "เปิด" : "ปิด"}${device.display_name || device.id}`;
  setText(els.deviceDetailActionStatus, `กำลังส่ง: ${commandText}`);

  try {
    const data = await sendChatMessage(commandText, { statusText: "กำลังส่งคำสั่งอุปกรณ์..." });
    setText(els.deviceDetailActionStatus, data?.reply || "ส่งคำสั่งแล้ว");
    await refreshAllStatus();
    renderSelectedDeviceDetail();
  } catch (error) {
    setText(els.deviceDetailActionStatus, "ส่งคำสั่งไม่สำเร็จ");
  }
}

function renderDeviceList(devices) {
  if (!els.mobileDeviceList) {
    return;
  }
  els.mobileDeviceList.innerHTML = "";
  if (!devices.length) {
    const empty = document.createElement("article");
    empty.innerHTML = `<i data-lucide="box" aria-hidden="true"></i><div><h2>ยังไม่มีอุปกรณ์</h2><p>เพิ่มอุปกรณ์ได้จาก Admin Dashboard</p></div><span class="device-badge">0</span>`;
    els.mobileDeviceList.appendChild(empty);
    return;
  }

  for (const device of devices) {
    const item = document.createElement("button");
    item.type = "button";
    item.addEventListener("click", () => {
      window.location.hash = `device:${encodeURIComponent(device.id)}`;
    });
    const detail = [
      device.room || "ไม่ระบุห้อง",
      device.gpio_pin !== null && device.gpio_pin !== undefined ? `GPIO ${device.gpio_pin}` : null,
      device.relay_channel ? `CH ${device.relay_channel}` : null,
    ].filter(Boolean).join(" • ");
    item.innerHTML = `
      <i data-lucide="${deviceIconName(device.device_type)}" aria-hidden="true"></i>
      <div>
        <h2>${escapeHtml(device.display_name || device.id)}</h2>
        <p>${escapeHtml(detail || device.device_type)}</p>
      </div>
      <span class="device-badge ${device.enabled ? "enabled" : ""}">${device.enabled ? "เปิดใช้" : "ปิด"}</span>
    `;
    els.mobileDeviceList.appendChild(item);
  }

  window.lucide?.createIcons();
}

async function refreshDeviceRegistryStatus() {
  if (state.demoMode) {
    state.deviceRegistryStatus = {
      ...DEMO_DEVICE_STATUS,
      devices: DEMO_DEVICE_STATUS.devices.map((device) => ({
        ...device,
        last_updated_at: device.last_updated_at || new Date().toISOString(),
      })),
    };
    setText(els.statusDevices, `${DEMO_DEVICE_STATUS.enabled}/${DEMO_DEVICE_STATUS.total} demo`);
    setText(els.devicesSummary, `Demo Mode: มีอุปกรณ์ ${DEMO_DEVICE_STATUS.total} รายการ`);
    renderDeviceList(state.deviceRegistryStatus.devices);
    if (state.currentView === "device-detail") {
      renderSelectedDeviceDetail();
    }
    return;
  }

  try {
    const { response, data } = await fetchJson("/devices/status", {}, 8000);
    if (!response.ok) {
      throw new Error("device status failed");
    }
    state.deviceRegistryStatus = data;
    const devices = Array.isArray(data.devices) ? data.devices : [];
    setText(els.statusDevices, `${data.enabled || 0}/${data.total || 0} เปิดใช้`);
    setText(els.devicesSummary, `มีอุปกรณ์ ${data.total || 0} รายการ เปิดใช้งาน ${data.enabled || 0} รายการ`);
    renderDeviceList(devices);
    if (state.currentView === "device-detail") {
      renderSelectedDeviceDetail();
    }
  } catch (error) {
    state.deviceRegistryStatus = null;
    setText(els.statusDevices, "รอข้อมูล");
    setText(els.devicesSummary, "โหลดรายการอุปกรณ์ไม่สำเร็จ");
    if (state.currentView === "device-detail") {
      renderSelectedDeviceDetail();
    }
  }
}

async function refreshAllStatus() {
  await Promise.allSettled([
    refreshDashboardStatus(),
    refreshVoiceNodeStatus(),
    refreshDeviceRegistryStatus(),
  ]);
}

async function sendChatMessage(message, options = {}) {
  const text = message.trim();
  if (!text) {
    return null;
  }
  appendChatBubble("user", text);
  clearChatStatusTimers();
  setChatBusy(true);
  updateChatStatus({
    title: "ส่งคำสั่งแล้ว",
    detail: options.statusText || "กำลังส่งข้อความให้น้องฟ้า",
    label: "กำลังส่ง",
    tone: "busy",
    activeStep: "input",
    completedSteps: ["input"],
  });
  queueChatStatus(700, {
    title: "AI กำลังประมวลผล",
    detail: "กำลังตีความคำสั่งและเลือกบริการที่เกี่ยวข้อง",
    label: "กำลังคิด",
    tone: "busy",
    activeStep: "thinking",
    completedSteps: ["input"],
  });
  queueChatStatus(2600, {
    title: "รอคำตอบจาก AI",
    detail: "AI กำลังเตรียมคำตอบกลับมาให้",
    label: "กำลังตอบ",
    tone: "busy",
    activeStep: "reply",
    completedSteps: ["input", "thinking"],
  });

  try {
    const { response, data } = await fetchJson(
      "/chat",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      },
      70000
    );

    if (!response.ok) {
      throw new Error(data.detail || "chat request failed");
    }

    clearChatStatusTimers();
    updateChatStatus({
      title: "AI ตอบกลับแล้ว",
      detail: data.intent ? `เสร็จแล้ว • ${data.intent}` : "เสร็จแล้ว",
      label: "สำเร็จ",
      tone: "success",
      activeStep: "reply",
      completedSteps: ["input", "thinking", "reply"],
    });
    setText(els.chatReply, data.reply || "น้องฟ้าตอบกลับแล้ว");
    appendChatBubble("assistant", data.reply || "น้องฟ้าตอบกลับแล้ว");
    if (data.audio_url) {
      updateChatStatus({
        title: "AI ตอบกลับแล้ว",
        detail: "กำลังเตรียมเสียงตอบกลับ",
        label: "มีเสียงตอบ",
        tone: "success",
        activeStep: "reply",
        completedSteps: ["input", "thinking", "reply"],
        mirrorToFooter: false,
      });
      let audioPlaybackOk = false;
      if (options.awaitAudio) {
        audioPlaybackOk = await playReplyAudio(data.audio_url);
      } else {
        void playReplyAudio(data.audio_url);
      }
      data.audio_playback_ok = audioPlaybackOk;
    } else if (options.awaitAudio) {
      data.audio_playback_ok = false;
    }
    await refreshDashboardStatus();
    return data;
  } catch (error) {
    clearChatStatusTimers();
    updateChatStatus({
      title: "ส่งคำสั่งไม่สำเร็จ",
      detail: "ลองส่งข้อความอีกครั้ง หรือเช็คสถานะ backend",
      label: "ผิดพลาด",
      tone: "warn",
      activeStep: "input",
      completedSteps: [],
    });
    throw error;
  } finally {
    clearChatStatusTimers();
    setChatBusy(false);
  }
}

async function sendVoiceTextMessage(message) {
  const text = message.trim();
  if (!text) {
    return null;
  }
  appendChatBubble("user", text);
  clearChatStatusTimers();
  setChatBusy(true);
  updateChatStatus({
    title: "ส่งคำสั่งเสียงแล้ว",
    detail: `คำสั่งเสียง: ${text}`,
    label: "กำลังส่ง",
    tone: "busy",
    activeStep: "input",
    completedSteps: ["audio", "stt"],
  });
  queueChatStatus(700, {
    title: "AI กำลังประมวลผล",
    detail: "กำลังตีความคำสั่งเสียงผ่านโหมดสนทนา",
    label: "กำลังคิด",
    tone: "busy",
    activeStep: "thinking",
    completedSteps: ["audio", "stt", "input"],
  });
  queueChatStatus(2600, {
    title: "รอคำตอบจาก AI",
    detail: "กำลังเตรียมคำตอบและเสียงตอบกลับ",
    label: "กำลังตอบ",
    tone: "busy",
    activeStep: "reply",
    completedSteps: ["audio", "stt", "input", "thinking"],
  });

  try {
    const formData = new FormData();
    formData.append("message", text);
    formData.append("pir_state", "0");

    const { response, data } = await fetchJson(
      "/voice/chat",
      {
        method: "POST",
        body: formData,
      },
      80000
    );

    if (!response.ok) {
      throw new Error(data.detail || "voice chat failed");
    }

    const result = data.data || data;
    const heardText = (result.heard_text || text).trim();
    const reply = result.reply || "น้องฟ้าตอบกลับแล้ว";
    clearChatStatusTimers();
    updateChatStatus({
      title: "AI ตอบกลับแล้ว",
      detail: heardText ? `คำสั่งเสียง: ${heardText}` : "ประมวลผลคำสั่งเสียงแล้ว",
      label: "สำเร็จ",
      tone: "success",
      activeStep: "reply",
      completedSteps: ["audio", "stt", "input", "thinking", "reply"],
      mirrorToFooter: false,
    });
    setVoiceStatus(heardText ? `ได้ยิน: ${heardText}` : "น้องฟ้าตอบกลับแล้ว", "success");
    setVoiceTranscript(heardText || text, "success");
    setText(els.chatReply, reply);
    appendChatBubble("assistant", reply);

    if (result.audio_url) {
      updateChatStatus({
        title: "AI ตอบกลับแล้ว",
        detail: "กำลังเตรียมเสียงตอบกลับ",
        label: "มีเสียงตอบ",
        tone: "success",
        activeStep: "reply",
        completedSteps: ["audio", "stt", "input", "thinking", "reply"],
        mirrorToFooter: false,
      });
      result.audio_playback_ok = await playReplyAudio(result.audio_url);
    } else {
      result.audio_playback_ok = false;
    }
    await refreshDashboardStatus();
    return result;
  } catch (error) {
    clearChatStatusTimers();
    updateChatStatus({
      title: "ส่งคำสั่งเสียงไม่สำเร็จ",
      detail: "ลองพูดใหม่อีกครั้ง หรือเช็คสถานะ backend",
      label: "ผิดพลาด",
      tone: "warn",
      activeStep: "input",
      completedSteps: ["audio", "stt"],
    });
    throw error;
  } finally {
    clearChatStatusTimers();
    setChatBusy(false);
  }
}

function updatePhoneWakeUi() {
  const text = state.phoneWakeListening
    ? "มือถือกำลังรอคำว่า น้องฟ้า"
    : "ยังไม่ได้เปิด";
  setText(els.phoneWakeStatus, text);
  setText(els.wakeSummaryStatus, state.phoneWakeListening ? text : "ใช้ได้เมื่อแอปเปิดอยู่และได้รับอนุญาตไมค์");
  setText(
    els.statusWakeDetail,
    state.phoneWakeListening
      ? text
      : state.voiceNodeStatus?.wake_mode_enabled
        ? "Voice Node กำลังรอคำปลุก"
        : "ยังไม่ได้เปิด Wake Mode"
  );
}

function setDiagnostic(element, tone, detail) {
  if (!element) {
    return;
  }
  element.setAttribute("data-tone", tone);
  const detailElement = element.querySelector("p");
  if (detailElement) {
    detailElement.textContent = detail;
  }
}

function isStandaloneApp() {
  return window.matchMedia?.("(display-mode: standalone)")?.matches || window.navigator.standalone === true;
}

function updateInstallUi() {
  state.appInstalled = isStandaloneApp() || state.appInstalled;
  if (state.appInstalled) {
    setText(els.settingsInstallStatus, "ติดตั้งแล้ว");
    setText(els.settingsInstallApp, "ติดตั้งแล้ว");
    if (els.settingsInstallApp) {
      els.settingsInstallApp.disabled = true;
    }
    return;
  }

  const canPrompt = Boolean(state.deferredInstallPrompt);
  setText(els.settingsInstallStatus, canPrompt ? "พร้อมติดตั้งผ่าน browser" : "ใช้เมนู browser เพื่อ Add to Home Screen");
  setText(els.settingsInstallApp, canPrompt ? "ติดตั้ง" : "พร้อม");
  if (els.settingsInstallApp) {
    els.settingsInstallApp.disabled = false;
  }
}

function updateApiBaseUi(status = "") {
  setText(els.settingsApiBaseCurrent, apiBaseLabel());
  if (els.settingsApiBaseInput) {
    els.settingsApiBaseInput.value = apiBase;
  }
  setText(els.settingsApiBaseStatus, status || (apiBase ? "ใช้ backend แยก origin" : "ใช้ same-origin ถ้าไม่ตั้งค่า"));
}

function updateDemoModeUi() {
  setText(els.settingsDemoToggle, state.demoMode ? "เปิด" : "ปิด");
  setText(els.settingsDemoStatus, state.demoMode ? "กำลังใช้ข้อมูลจำลองสำหรับ UI" : "ใช้ข้อมูลจริงจาก backend");
  els.settingsDemoToggle?.setAttribute("aria-pressed", String(state.demoMode));
}

function updateSettingsUi() {
  updateInstallUi();
  updateApiBaseUi();
  updateDemoModeUi();
}

async function getMicrophonePermissionState() {
  if (!navigator.permissions?.query) {
    return "";
  }
  try {
    const permission = await navigator.permissions.query({ name: "microphone" });
    return permission.state || "";
  } catch (error) {
    return "";
  }
}

async function refreshDiagnostics() {
  const secureDetail = window.isSecureContext ? "พร้อมใช้งานไมค์" : "ต้องใช้ HTTPS หรือ localhost";
  setDiagnostic(els.diagSecure, window.isSecureContext ? "success" : "warn", secureDetail);

  const micSupported = Boolean(navigator.mediaDevices?.getUserMedia && window.MediaRecorder);
  const micPermission = await getMicrophonePermissionState();
  const micDetail = micSupported
    ? `รองรับการอัดเสียง${micPermission ? ` • permission: ${micPermission}` : ""}`
    : "browser นี้ยังไม่รองรับ MediaRecorder";
  setDiagnostic(els.diagMic, micSupported ? "success" : "warn", micDetail);

  setDiagnostic(
    els.diagSpeech,
    SpeechRecognitionConstructor ? "success" : "warn",
    SpeechRecognitionConstructor ? "รองรับ wake listening แบบ foreground" : "ใช้ Push-to-Talk แทนได้"
  );

  const hasServiceWorker = "serviceWorker" in navigator;
  setDiagnostic(
    els.diagServiceWorker,
    hasServiceWorker ? "success" : "warn",
    hasServiceWorker ? "พร้อม cache PWA shell" : "browser นี้ไม่มี service worker"
  );

  const standalone = isStandaloneApp();
  setDiagnostic(
    els.diagPwa,
    standalone ? "success" : "busy",
    standalone
      ? "กำลังเปิดแบบ installed app"
      : state.deferredInstallPrompt
        ? "พร้อมแสดง install prompt"
        : "เปิดแบบ browser tab"
  );

  setDiagnostic(els.diagApi, "busy", apiBaseLabel());
  try {
    const { response } = await fetchJson("/dashboard/status", {}, 6000);
    setDiagnostic(els.diagApi, response.ok ? "success" : "warn", response.ok ? "backend ตอบกลับแล้ว" : "backend ตอบกลับไม่สมบูรณ์");
  } catch (error) {
    setDiagnostic(els.diagApi, "warn", "ติดต่อ backend ไม่สำเร็จ");
  }
}

async function testMicrophonePermission() {
  if (!window.isSecureContext) {
    state.voiceConversationMode = false;
    setText(els.settingsMicTestStatus, "ต้องเปิดผ่าน HTTPS หรือ localhost");
    await refreshDiagnostics();
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    setText(els.settingsMicTestStatus, "browser นี้ไม่รองรับไมค์");
    await refreshDiagnostics();
    return;
  }

  setText(els.settingsMicTestStatus, "กำลังขออนุญาตไมค์...");
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    for (const track of stream.getTracks()) {
      track.stop();
    }
    setText(els.settingsMicTestStatus, "ไมค์พร้อมใช้งาน");
  } catch (error) {
    const denied = error?.name === "NotAllowedError" || error?.name === "PermissionDeniedError";
    setText(els.settingsMicTestStatus, denied ? "ผู้ใช้ยังไม่อนุญาตไมค์" : "เปิดไมค์ไม่สำเร็จ");
  }
  await refreshDiagnostics();
}

function setDemoMode(enabled) {
  state.demoMode = enabled;
  writeStorage(DEMO_MODE_STORAGE_KEY, enabled ? "1" : "");
  updateDemoModeUi();
  void refreshAllStatus();
}

async function promptInstallApp() {
  if (isStandaloneApp()) {
    updateInstallUi();
    return;
  }
  if (!state.deferredInstallPrompt) {
    setText(els.settingsInstallStatus, "ใช้เมนู browser เพื่อ Add to Home Screen");
    return;
  }

  const promptEvent = state.deferredInstallPrompt;
  state.deferredInstallPrompt = null;
  promptEvent.prompt();
  try {
    const choice = await promptEvent.userChoice;
    setText(els.settingsInstallStatus, choice?.outcome === "accepted" ? "กำลังติดตั้ง" : "ยังไม่ได้ติดตั้ง");
  } catch (error) {
    setText(els.settingsInstallStatus, "เปิด install prompt แล้ว");
  }
  updateInstallUi();
  void refreshDiagnostics();
}

async function saveApiBaseFromSettings() {
  const rawValue = els.settingsApiBaseInput?.value || "";
  const normalized = normalizeApiBase(rawValue);
  if (rawValue.trim() && !normalized) {
    updateApiBaseUi("URL ไม่ถูกต้อง");
    return;
  }
  apiBase = normalized;
  writeStorage(API_BASE_STORAGE_KEY, apiBase);
  updateApiBaseUi(apiBase ? "บันทึก backend URL แล้ว" : "กลับไปใช้ same-origin แล้ว");
  await refreshDiagnostics();
  await refreshAllStatus();
}

async function testApiBaseFromSettings() {
  updateApiBaseUi("กำลังทดสอบ backend...");
  try {
    const { response } = await fetchJson("/dashboard/status", {}, 8000);
    updateApiBaseUi(response.ok ? "backend ตอบกลับแล้ว" : "backend ตอบกลับไม่สมบูรณ์");
  } catch (error) {
    updateApiBaseUi("ติดต่อ backend ไม่สำเร็จ");
  }
  await refreshDiagnostics();
}

async function resetApiBaseSettings() {
  apiBase = normalizeApiBase(DEFAULT_API_BASE);
  writeStorage(API_BASE_STORAGE_KEY, "");
  updateApiBaseUi(apiBase ? "กลับไปใช้ค่าเริ่มต้น" : "กลับไปใช้ same-origin");
  await refreshDiagnostics();
  await refreshAllStatus();
}

function stopPhoneWakeMode() {
  state.phoneWakeListening = false;
  if (state.wakeRecognition) {
    state.wakeRecognition.onresult = null;
    state.wakeRecognition.onerror = null;
    state.wakeRecognition.onend = null;
    try {
      state.wakeRecognition.stop();
    } catch (error) {
      // Already stopped.
    }
  }
  state.wakeRecognition = null;
  updatePhoneWakeUi();
}

function startPhoneWakeMode() {
  if (!window.isSecureContext) {
    setText(els.phoneWakeStatus, "ต้องเปิดผ่าน HTTPS หรือ localhost");
    return;
  }
  if (!SpeechRecognitionConstructor) {
    setText(els.phoneWakeStatus, "browser นี้ไม่รองรับ wake listening");
    setVoiceStatus("ใช้ Push-to-Talk แทน Wake Mode ได้", "warn");
    return;
  }

  stopPhoneWakeMode();
  const recognition = new SpeechRecognitionConstructor();
  recognition.lang = "th-TH";
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  recognition.onresult = (event) => {
    const transcript = collectSpeechText(event);
    if (!transcript) {
      return;
    }
    setText(els.phoneWakeStatus, `กำลังฟัง: ${transcript}`);
    if (detectWakeWord(transcript)) {
      setVoiceStatus("ได้ยินคำปลุกแล้ว กำลังเปิดรอบสนทนา", "live");
      stopPhoneWakeMode();
      window.setTimeout(() => void startBrowserSpeechTurn({ resumeWakeOnEnd: true }), 250);
    }
  };
  recognition.onerror = (event) => {
    setText(els.phoneWakeStatus, event.error ? `Wake error: ${event.error}` : "Wake error");
  };
  recognition.onend = () => {
    if (state.phoneWakeListening) {
      try {
        recognition.start();
      } catch (error) {
        state.phoneWakeListening = false;
        updatePhoneWakeUi();
      }
    }
  };

  try {
    recognition.start();
    state.wakeRecognition = recognition;
    state.phoneWakeListening = true;
    updatePhoneWakeUi();
    setVoiceStatus("Wake Mode เปิดอยู่ พูดว่า น้องฟ้า", "live");
  } catch (error) {
    state.phoneWakeListening = false;
    setText(els.phoneWakeStatus, "เปิด Wake Mode ไม่สำเร็จ");
    updatePhoneWakeUi();
  }
}

async function queueVoiceNodeWakeCommand(action) {
  const path = action === "start"
    ? "/voice-node/commands/wake-listen-start?device_id=voice-node-01"
    : "/voice-node/commands/wake-listen-stop?device_id=voice-node-01";
  const { response, data } = await fetchJson(path, { method: "POST" }, 10000);
  if (!response.ok) {
    throw new Error(data.detail || "voice node wake command failed");
  }
  await refreshVoiceNodeStatus();
}

function getSupportedRecordingMimeType() {
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/ogg;codecs=opus",
  ];
  for (const candidate of candidates) {
    if (window.MediaRecorder?.isTypeSupported(candidate)) {
      return candidate;
    }
  }
  return "";
}

function audioExtension(mimeType) {
  if (mimeType.includes("mp4")) {
    return "m4a";
  }
  if (mimeType.includes("ogg")) {
    return "ogg";
  }
  return "webm";
}

function stopMediaStream() {
  if (state.voiceVadTimer) {
    window.cancelAnimationFrame(state.voiceVadTimer);
    state.voiceVadTimer = 0;
  }
  if (state.audioContext) {
    void state.audioContext.close().catch(() => {});
  }
  state.audioContext = null;
  state.analyser = null;
  if (state.mediaStream) {
    for (const track of state.mediaStream.getTracks()) {
      track.stop();
    }
  }
  state.mediaStream = null;
}

function startVoiceActivityMonitor(stream) {
  if (state.voiceVadTimer) {
    window.cancelAnimationFrame(state.voiceVadTimer);
  }
  const AudioContextConstructor = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextConstructor) {
    return;
  }
  const audioContext = new AudioContextConstructor();
  const source = audioContext.createMediaStreamSource(stream);
  const analyser = audioContext.createAnalyser();
  analyser.fftSize = 1024;
  source.connect(analyser);

  state.audioContext = audioContext;
  state.analyser = analyser;
  state.voiceRecordingStartedAt = Date.now();
  state.voiceLastSpeechAt = 0;
  state.voiceSpeechStarted = false;
  const samples = new Uint8Array(analyser.fftSize);

  const tick = () => {
    if (!state.mediaRecorder || state.mediaRecorder.state !== "recording") {
      return;
    }
    analyser.getByteTimeDomainData(samples);
    let sumSquares = 0;
    for (const value of samples) {
      const normalized = (value - 128) / 128;
      sumSquares += normalized * normalized;
    }
    const rms = Math.sqrt(sumSquares / samples.length);
    const now = Date.now();
    const elapsedMs = now - state.voiceRecordingStartedAt;
    if (rms >= RECORDING_RMS_THRESHOLD) {
      state.voiceSpeechStarted = true;
      state.voiceLastSpeechAt = now;
    }
    if (
      state.voiceSpeechStarted &&
      elapsedMs >= RECORDING_MIN_MS &&
      now - state.voiceLastSpeechAt >= RECORDING_SILENCE_STOP_MS
    ) {
      stopRecording();
      return;
    }
    if (!state.voiceSpeechStarted && elapsedMs >= RECORDING_NO_SPEECH_STOP_MS) {
      stopRecording();
      return;
    }
    state.voiceVadTimer = window.requestAnimationFrame(tick);
  };

  state.voiceVadTimer = window.requestAnimationFrame(tick);
}

function stopVoiceRecognition(options = {}) {
  window.clearTimeout(state.voiceRecognitionTimeout);
  state.voiceRecognitionTimeout = 0;
  window.clearTimeout(state.voiceContinueTimer);
  state.voiceContinueTimer = 0;
  if (state.voiceRecognition) {
    state.voiceRecognition.onresult = null;
    state.voiceRecognition.onerror = null;
    state.voiceRecognition.onend = null;
    try {
      if (typeof state.voiceRecognition.abort === "function") {
        state.voiceRecognition.abort();
      } else {
        state.voiceRecognition.stop();
      }
    } catch (error) {
      try {
        state.voiceRecognition.stop();
      } catch (stopError) {
        // Already stopped.
      }
    }
  }
  state.voiceRecognition = null;
  els.voiceOrb?.classList.remove("is-recording");
  if (options.resetBusy) {
    state.voiceBusy = false;
    setChatBusy(false);
  }
  if (!options.keepConversation) {
    state.voiceConversationMode = false;
    state.voiceTurnId += 1;
  }
}

function resumePhoneWakeAfterVoiceTurn() {
  if (!state.voiceResumeWakeAfterTurn) {
    return;
  }
  state.voiceResumeWakeAfterTurn = false;
  if (!SpeechRecognitionConstructor || state.phoneWakeListening || state.voiceBusy) {
    return;
  }
  window.setTimeout(() => {
    if (!state.voiceBusy && !state.phoneWakeListening) {
      startPhoneWakeMode();
    }
  }, 700);
}

async function startBrowserSpeechTurn(options = {}) {
  const continueConversation = Boolean(options.continueConversation);
  if (!continueConversation) {
    state.voiceConversationMode = true;
  }
  state.voiceTurnId += 1;
  const turnId = state.voiceTurnId;
  if (options.resumeWakeOnEnd) {
    state.voiceResumeWakeAfterTurn = true;
  }
  if (!SpeechRecognitionConstructor) {
    return startRecording(options);
  }
  if (!window.isSecureContext) {
    state.voiceConversationMode = false;
    setVoiceStatus("ต้องเปิดผ่าน HTTPS หรือ localhost เพื่อใช้ไมค์มือถือ", "warn");
    updateChatStatus({
      title: "เปิดไมค์ไม่ได้",
      detail: "ต้องเปิดผ่าน HTTPS หรือ localhost",
      label: "ไมค์ปิด",
      tone: "warn",
      activeStep: "audio",
      completedSteps: [],
    });
    return null;
  }
  if (state.voiceBusy || state.voiceRecognition) {
    updateChatStatus({
      title: "กำลังทำงานกับคำสั่งเสียงเดิม",
      detail: "รอให้รอบก่อนหน้าจบก่อน",
      label: "กำลังทำงาน",
      tone: "busy",
      activeStep: "stt",
      completedSteps: ["audio"],
    });
    return null;
  }

  let settled = false;
  let lastTranscript = "";
  let recognition = null;
  const listenStartedAt = Date.now();
  let retryNoSpeech = false;

  const canKeepListening = () =>
    !settled &&
    state.voiceTurnId === turnId &&
    Date.now() - listenStartedAt < BROWSER_SPEECH_LISTEN_MAX_MS - BROWSER_SPEECH_RESTART_GRACE_MS;

  const restartListening = () => {
    if (!canKeepListening()) {
      return false;
    }
    try {
      recognition.start();
      setVoiceStatus("ยังรอฟังอยู่ พูดคำสั่งได้เลย", "live");
      setVoiceTranscript(lastTranscript || "กำลังรอฟังคำสั่งเสียง", "live");
      return true;
    } catch (error) {
      return false;
    }
  };

  const finishTurn = async (reason) => {
    if (settled) {
      return null;
    }
    settled = true;
    window.clearTimeout(state.voiceRecognitionTimeout);
    state.voiceRecognitionTimeout = 0;
    state.voiceRecognition = null;
    els.voiceOrb?.classList.remove("is-recording");
    const transcript = lastTranscript.trim();

    if (!transcript) {
      clearChatStatusTimers();
      setVoiceStatus(reason === "timeout" ? "ไม่ได้ยินคำสั่งในเวลาที่กำหนด" : "ยังไม่ได้ยินคำสั่งชัดเจน", "warn");
      setVoiceTranscript("ยังไม่ได้ยินคำสั่งเสียง", "warn");
      updateChatStatus({
        title: "ยังไม่ได้ยินคำสั่ง",
        detail: "ปิดการฟังแล้ว เรียกหรือกดพูดใหม่ได้",
        label: "ไม่ได้ยิน",
        tone: "warn",
        activeStep: "audio",
        completedSteps: [],
      });
      state.voiceBusy = false;
      setChatBusy(false);
      state.voiceConversationMode = false;
      resumePhoneWakeAfterVoiceTurn();
      return null;
    }

    setVoiceStatus(`ได้ยิน: ${transcript}`, "success");
    setVoiceTranscript(transcript, "success");
    updateChatStatus({
      title: "ถอดเสียงจากมือถือแล้ว",
      detail: `คำสั่งเสียง: ${transcript}`,
      label: "ได้ยินแล้ว",
      tone: "success",
      activeStep: "stt",
      completedSteps: ["audio", "stt"],
    });

    try {
      const data = await sendVoiceTextMessage(transcript);
      if (shouldEndVoiceConversation(transcript) || data?.keep_mic_open === false) {
        state.voiceConversationMode = false;
      }
      if (data?.audio_playback_ok === false) {
        state.voiceConversationMode = false;
        updateChatStatus({
          title: "AI ตอบกลับแล้ว",
          detail: "เสียงตอบยังไม่พร้อมหรือถูกแทนที่ กดไมค์อีกครั้งเมื่ออยากคุยต่อ",
          label: "รอกดต่อ",
          tone: "warn",
          activeStep: "reply",
          completedSteps: ["input", "thinking", "reply"],
          mirrorToFooter: false,
        });
      }
      state.voiceBusy = false;
      if (state.voiceConversationMode) {
        window.clearTimeout(state.voiceContinueTimer);
        state.voiceContinueTimer = window.setTimeout(() => {
          if (!state.voiceBusy && state.voiceConversationMode && state.voiceTurnId === turnId) {
            void startBrowserSpeechTurn({
              continueConversation: true,
              resumeWakeOnEnd: state.voiceResumeWakeAfterTurn,
            });
          }
        }, VOICE_CONTINUE_DELAY_MS);
      } else {
        resumePhoneWakeAfterVoiceTurn();
      }
      return data;
    } catch (error) {
      state.voiceBusy = false;
      state.voiceConversationMode = false;
      setVoiceStatus("ส่งคำสั่งเสียงไม่สำเร็จ ลองใหม่อีกครั้ง", "warn");
      setVoiceTranscript(transcript, "warn");
      resumePhoneWakeAfterVoiceTurn();
      return null;
    }
  };

  try {
    recognition = new SpeechRecognitionConstructor();
    recognition.lang = "th-TH";
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    state.voiceRecognition = recognition;
    state.voiceBusy = true;
    els.voiceOrb?.classList.add("is-recording");
    setVoiceStatus("กำลังฟังผ่านไมค์มือถือ...", "live");
    setVoiceTranscript("กำลังรอฟังคำสั่งเสียง", "live");
    clearChatStatusTimers();
    updateChatStatus({
      title: "กำลังฟังคำสั่งเสียง",
      detail: "มือถือกำลังถอดเสียงเป็นข้อความแบบสด",
      label: "กำลังฟัง",
      tone: "live",
      activeStep: "audio",
      completedSteps: [],
    });

    recognition.onresult = (event) => {
      const parts = [];
      let hasFinal = false;
      for (let index = 0; index < event.results.length; index += 1) {
        const result = event.results[index];
        const transcript = result?.[0]?.transcript;
        if (transcript) {
          parts.push(transcript);
        }
        hasFinal = hasFinal || Boolean(result?.isFinal);
      }
      lastTranscript = parts.join(" ").trim();
      if (lastTranscript) {
        setVoiceStatus(`กำลังฟัง: ${lastTranscript}`, "live");
        setVoiceTranscript(lastTranscript, hasFinal ? "success" : "live");
      }
      if (hasFinal && lastTranscript) {
        try {
          recognition.stop();
        } catch (error) {
          // Some browsers auto-stop once a final result is produced.
        }
        void finishTurn("final");
      }
    };

    recognition.onerror = (event) => {
      if (event.error === "no-speech" && !lastTranscript && canKeepListening()) {
        retryNoSpeech = true;
        setVoiceStatus("ยังรอฟังอยู่ พูดคำสั่งได้เลย", "live");
        return;
      }
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        lastTranscript = "";
        setVoiceStatus("ยังไม่ได้อนุญาตใช้ไมค์", "warn");
      }
      void finishTurn(event.error || "error");
    };

    recognition.onend = () => {
      if (!lastTranscript && (retryNoSpeech || canKeepListening())) {
        retryNoSpeech = false;
        window.setTimeout(() => {
          if (restartListening()) {
            return;
          }
          void finishTurn("end");
        }, 120);
        return;
      }
      void finishTurn("end");
    };

    recognition.onspeechend = () => {
      window.setTimeout(() => {
        if (lastTranscript && !settled && state.voiceTurnId === turnId) {
          try {
            recognition.stop();
          } catch (error) {
            // Some browsers stop automatically after speech ends.
          }
        }
      }, BROWSER_SPEECH_RESTART_GRACE_MS);
    };

    recognition.start();
    window.clearTimeout(state.voiceRecognitionTimeout);
    state.voiceRecognitionTimeout = window.setTimeout(() => {
      try {
        recognition.stop();
      } catch (error) {
        // Already stopped.
      }
      void finishTurn("timeout");
    }, BROWSER_SPEECH_LISTEN_MAX_MS);
    return null;
  } catch (error) {
    stopVoiceRecognition({ resetBusy: true });
    setVoiceStatus("เปิดการถอดเสียงจาก browser ไม่สำเร็จ กำลังใช้โหมดอัดเสียงแทน", "warn");
    return startRecording(options);
  }
}

async function startRecording(options = {}) {
  const continueConversation = Boolean(options.continueConversation);
  if (!continueConversation) {
    state.voiceConversationMode = true;
  }
  if (!window.isSecureContext) {
    state.voiceConversationMode = false;
    setVoiceStatus("ต้องเปิดผ่าน HTTPS หรือ localhost เพื่อใช้ไมค์มือถือ", "warn");
    updateChatStatus({
      title: "เปิดไมค์ไม่ได้",
      detail: "ต้องเปิดผ่าน HTTPS หรือ localhost",
      label: "ไมค์ปิด",
      tone: "warn",
      activeStep: "audio",
      completedSteps: [],
    });
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    state.voiceConversationMode = false;
    setVoiceStatus("เบราว์เซอร์นี้ยังไม่รองรับการอัดเสียง", "warn");
    updateChatStatus({
      title: "เบราว์เซอร์ไม่รองรับไมค์",
      detail: "ใช้การพิมพ์ข้อความแทนได้",
      label: "ไม่รองรับ",
      tone: "warn",
      activeStep: "audio",
      completedSteps: [],
    });
    return;
  }
  if (state.voiceBusy) {
    updateChatStatus({
      title: "กำลังประมวลผลเสียงเดิม",
      detail: "รอให้รอบก่อนหน้าจบก่อน",
      label: "กำลังทำงาน",
      tone: "busy",
      activeStep: "stt",
      completedSteps: ["audio", "upload"],
    });
    return;
  }

  try {
    clearChatStatusTimers();
    setVoiceTranscript("กำลังรอฟังคำสั่งเสียง", "live");
    updateChatStatus({
      title: "กำลังเตรียมไมค์",
      detail: "กำลังขออนุญาตใช้ไมค์มือถือ",
      label: "ขอสิทธิ์ไมค์",
      tone: "busy",
      activeStep: "audio",
      completedSteps: [],
    });
    setVoiceStatus("กำลังขออนุญาตไมค์...");
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    const mimeType = getSupportedRecordingMimeType();
    const mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    state.mediaStream = stream;
    state.mediaRecorder = mediaRecorder;
    state.audioChunks = [];

    mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data?.size) {
        state.audioChunks.push(event.data);
      }
    });
    mediaRecorder.addEventListener("stop", () => {
      void uploadRecordedAudio(mimeType || mediaRecorder.mimeType);
    });

    mediaRecorder.start();
    startVoiceActivityMonitor(stream);
    els.voiceOrb?.classList.add("is-recording");
    setVoiceStatus("กำลังฟังอยู่ พูดให้จบประโยคแล้วระบบจะส่งเอง", "live");
    updateChatStatus({
      title: "กำลังบันทึกเสียง",
      detail: "พูดให้จบประโยค ระบบจะหยุดและส่งให้อัตโนมัติ",
      label: "กำลังฟัง",
      tone: "live",
      activeStep: "audio",
      completedSteps: [],
    });
    window.clearTimeout(state.recordingTimeout);
    state.recordingTimeout = window.setTimeout(stopRecording, RECORDING_MAX_MS);
  } catch (error) {
    state.voiceConversationMode = false;
    stopMediaStream();
    const denied = error?.name === "NotAllowedError" || error?.name === "PermissionDeniedError";
    setVoiceStatus(denied ? "ยังไม่ได้อนุญาตใช้ไมค์" : "เปิดไมค์ไม่สำเร็จ", "warn");
    setVoiceTranscript("ยังไม่ได้รับเสียงจากไมค์", "warn");
    updateChatStatus({
      title: denied ? "ยังไม่ได้อนุญาตใช้ไมค์" : "เปิดไมค์ไม่สำเร็จ",
      detail: denied ? "ต้องอนุญาตไมค์ก่อนเริ่มคุยผ่านเสียง" : "ลองกดปุ่มเสียงอีกครั้ง",
      label: "ไมค์ปิด",
      tone: "warn",
      activeStep: "audio",
      completedSteps: [],
    });
  }
}

function stopRecording() {
  window.clearTimeout(state.recordingTimeout);
  state.recordingTimeout = 0;
  if (state.mediaRecorder && state.mediaRecorder.state !== "inactive") {
    updateChatStatus({
      title: "หยุดบันทึกแล้ว",
      detail: "กำลังเตรียมส่งเสียงไปแปลงเป็นข้อความ",
      label: "กำลังส่ง",
      tone: "busy",
      activeStep: "upload",
      completedSteps: ["audio"],
    });
    state.mediaRecorder.stop();
  }
}

async function uploadRecordedAudio(mimeType) {
  let shouldContinueConversation = false;
  els.voiceOrb?.classList.remove("is-recording");
  setVoiceStatus("กำลังส่งเสียงให้น้องฟ้า...");
  state.voiceBusy = true;
  setChatBusy(true);
  clearChatStatusTimers();
  updateChatStatus({
    title: "กำลังส่งเสียง",
    detail: "กำลังอัปโหลดเสียงจากมือถือ",
    label: "ส่งเสียง",
    tone: "busy",
    activeStep: "upload",
    completedSteps: ["audio"],
  });

  try {
    const blob = new Blob(state.audioChunks, { type: mimeType || "audio/webm" });
    state.audioChunks = [];
    stopMediaStream();

    if (!blob.size) {
      setVoiceStatus("ไม่ได้ยินเสียง ลองใหม่อีกครั้ง", "warn");
      setVoiceTranscript("ยังไม่ได้ยินเสียงคำสั่ง", "warn");
      updateChatStatus({
        title: "ไม่ได้ยินเสียง",
        detail: "ลองพูดใกล้ไมค์ขึ้นอีกครั้ง",
        label: "ไม่มีเสียง",
        tone: "warn",
        activeStep: "audio",
        completedSteps: [],
      });
      return;
    }

    const formData = new FormData();
    formData.append("audio", blob, `mobile-voice.${audioExtension(blob.type)}`);
    formData.append("pir_state", "0");

    updateChatStatus({
      title: "กำลังแปลงเสียง",
      detail: "ระบบกำลังถอดเสียงเป็นข้อความ แล้วส่งต่อให้ AI",
      label: "แปลงเสียง",
      tone: "busy",
      activeStep: "stt",
      completedSteps: ["audio", "upload"],
    });
    queueChatStatus(2400, {
      title: "AI กำลังประมวลผล",
      detail: "กำลังตีความคำสั่งเสียงและเลือกการทำงาน",
      label: "กำลังคิด",
      tone: "busy",
      activeStep: "thinking",
      completedSteps: ["audio", "upload", "stt"],
    });
    queueChatStatus(5600, {
      title: "AI กำลังตอบ",
      detail: "กำลังเตรียมคำตอบและเสียงตอบกลับ",
      label: "กำลังตอบ",
      tone: "busy",
      activeStep: "reply",
      completedSteps: ["audio", "upload", "stt", "thinking"],
    });

    const { response, data } = await fetchJson(
      "/voice/chat",
      {
        method: "POST",
        body: formData,
      },
      80000
    );

    if (!response.ok) {
      throw new Error(data.detail || "voice chat failed");
    }

    const result = data.data || data;
    shouldContinueConversation = Boolean(result.keep_mic_open);
    setVoiceStatus(result.heard_text ? `ได้ยิน: ${result.heard_text}` : "น้องฟ้าตอบกลับแล้ว");
    setVoiceTranscript(result.heard_text || "ยังไม่ได้ยินคำสั่งชัดเจน", result.heard_text ? "success" : "warn");
    clearChatStatusTimers();
    updateChatStatus({
      title: result.heard_text ? "AI ตอบกลับแล้ว" : "เสียงไม่ชัด",
      detail: result.heard_text ? `คำสั่งเสียง: ${result.heard_text}` : "ระบบยังไม่ได้ยินประโยคชัดเจน",
      label: result.heard_text ? "ได้ยินแล้ว" : "เสียงไม่ชัด",
      tone: result.heard_text ? "success" : "warn",
      activeStep: "reply",
      completedSteps: ["audio", "upload", "stt", "thinking", "reply"],
      mirrorToFooter: false,
    });
    setText(els.chatReply, result.reply || "น้องฟ้าตอบกลับแล้ว");
    if (result.heard_text) {
      appendChatBubble("user", result.heard_text);
    }
    appendChatBubble("assistant", result.reply || "น้องฟ้าตอบกลับแล้ว");
    if (result.audio_url) {
      updateChatStatus({
        title: "AI ตอบกลับแล้ว",
        detail: "กำลังเตรียมเสียงตอบกลับ",
        label: "มีเสียงตอบ",
        tone: "success",
        activeStep: "reply",
        completedSteps: ["audio", "upload", "stt", "thinking", "reply"],
        mirrorToFooter: false,
      });
      const audioPlaybackOk = await playReplyAudio(result.audio_url);
      if (!audioPlaybackOk) {
        shouldContinueConversation = false;
      }
    } else {
      shouldContinueConversation = false;
    }
    await refreshDashboardStatus();
  } catch (error) {
    stopMediaStream();
    setVoiceStatus("ส่งเสียงไม่สำเร็จ ลองใหม่อีกครั้ง", "warn");
    setVoiceTranscript("ส่งเสียงไม่สำเร็จ", "warn");
    clearChatStatusTimers();
    updateChatStatus({
      title: "ส่งเสียงไม่สำเร็จ",
      detail: "ลองบันทึกเสียงใหม่ หรือเช็ค backend/STT",
      label: "ผิดพลาด",
      tone: "warn",
      activeStep: "upload",
      completedSteps: ["audio"],
    });
  } finally {
    clearChatStatusTimers();
    state.voiceBusy = false;
    setChatBusy(false);
    if (state.voiceConversationMode && shouldContinueConversation) {
      window.setTimeout(() => {
        if (!state.voiceBusy && state.voiceConversationMode) {
          void startRecording({ continueConversation: true });
        }
      }, 500);
    } else {
      state.voiceConversationMode = false;
      resumePhoneWakeAfterVoiceTurn();
    }
  }
}

function handleVoiceTap() {
  if (state.voiceRecognition) {
    state.voiceResumeWakeAfterTurn = false;
    stopVoiceRecognition({ resetBusy: true });
    setVoiceStatus("หยุดฟังคำสั่งเสียงแล้ว", "neutral");
    setVoiceTranscript("หยุดฟังแล้ว", "neutral");
    updateChatStatus({
      title: "หยุดฟังแล้ว",
      detail: "กดปุ่มไมค์อีกครั้งเพื่อเริ่มคุยใหม่",
      label: "หยุดฟัง",
      tone: "neutral",
      activeStep: "audio",
      completedSteps: [],
    });
    return;
  }
  if (state.voiceBusy) {
    state.voiceConversationMode = false;
    state.voiceResumeWakeAfterTurn = false;
    updateChatStatus({
      title: "กำลังจบรอบเสียงเดิม",
      detail: "จะไม่เปิดฟังรอบถัดไปอัตโนมัติ",
      label: "กำลังทำงาน",
      tone: "busy",
      activeStep: "stt",
      completedSteps: ["audio", "upload"],
    });
    return;
  }
  if (state.mediaRecorder && state.mediaRecorder.state === "recording") {
    state.voiceConversationMode = false;
    state.voiceResumeWakeAfterTurn = false;
    stopRecording();
    return;
  }
  void startBrowserSpeechTurn();
}

function getAudioToken(url) {
  try {
    return new URL(url, window.location.origin).searchParams.get("token");
  } catch (error) {
    return null;
  }
}

async function waitForAudioReady(audioUrl) {
  const token = getAudioToken(audioUrl);
  if (!token) {
    return { ok: true, reason: "no-token" };
  }
  let lastStatus = null;
  let lastError = null;
  const startedAt = Date.now();
  while (Date.now() - startedAt < REPLY_AUDIO_READY_TIMEOUT_MS) {
    try {
      const { response, data } = await fetchJson("/voice/status", {}, 8000);
      if (response.ok) {
        lastStatus = data;
        if (data.current_token === token && data.audio_ready) {
          return { ok: true, reason: "ready" };
        }
        if (data.current_token && data.current_token !== token) {
          return {
            ok: false,
            reason: data.last_error ? "failed" : "superseded",
            status: data,
          };
        }
        if (data.current_token === token && data.last_error) {
          return { ok: false, reason: "failed", status: data };
        }
      }
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => window.setTimeout(resolve, REPLY_AUDIO_STATUS_POLL_MS));
  }
  return {
    ok: false,
    reason: lastStatus?.current_token && lastStatus.current_token !== token ? "superseded" : "timeout",
    status: lastStatus,
    error: lastError,
  };
}

async function playReplyAudio(audioUrl) {
  try {
    updateChatStatus({
      title: "กำลังเตรียมเสียงตอบกลับ",
      detail: "กำลังรอไฟล์เสียงจากระบบ TTS",
      label: "เตรียมเสียง",
      tone: "busy",
      activeStep: "reply",
      completedSteps: ["input", "audio", "upload", "stt", "thinking", "reply"],
      mirrorToFooter: false,
    });
    const readyResult = await waitForAudioReady(audioUrl);
    if (!readyResult.ok) {
      updateChatStatus({
        title: "เสียงตอบยังไม่พร้อม",
        detail: readyResult.reason === "failed"
          ? "AI ตอบข้อความแล้ว แต่ระบบสร้างเสียงไม่สำเร็จ"
          : readyResult.reason === "superseded"
            ? "เสียงตอบรอบนี้ถูกแทนที่ด้วยรอบใหม่แล้ว"
            : "AI ตอบข้อความแล้ว แต่ระบบ TTS ยังสร้างเสียงไม่ทัน",
        label: "ไม่มีเสียงตอบ",
        tone: "warn",
        activeStep: "reply",
        completedSteps: ["input", "audio", "upload", "stt", "thinking", "reply"],
        mirrorToFooter: false,
      });
      return false;
    }
    const audio = new Audio(apiUrl(audioUrl));
    const endedPromise = new Promise((resolve, reject) => {
      audio.addEventListener("ended", resolve, { once: true });
      audio.addEventListener("error", () => reject(new Error("reply audio failed")), { once: true });
    });
    audio.addEventListener("ended", () => {
      updateChatStatus({
        title: "เล่นเสียงตอบกลับแล้ว",
        detail: "AI ตอบกลับเสร็จแล้ว",
        label: "สำเร็จ",
        tone: "success",
        activeStep: "reply",
        completedSteps: ["input", "audio", "upload", "stt", "thinking", "reply"],
        mirrorToFooter: false,
      });
    }, { once: true });
    await audio.play();
    updateChatStatus({
      title: "กำลังเล่นเสียงตอบกลับ",
      detail: "AI กำลังตอบผ่านลำโพงมือถือ",
      label: "กำลังพูด",
      tone: "live",
      activeStep: "reply",
      completedSteps: ["input", "audio", "upload", "stt", "thinking", "reply"],
      mirrorToFooter: false,
    });
    await endedPromise;
    return true;
  } catch (error) {
    updateChatStatus({
      title: "เสียงตอบเล่นไม่ได้",
      detail: "AI ตอบเป็นข้อความแล้ว แต่เสียงตอบไม่พร้อม กดไมค์เพื่อคุยต่อเอง",
      label: "ไม่มีเสียงตอบ",
      tone: "warn",
      activeStep: "reply",
      completedSteps: ["input", "audio", "upload", "stt", "thinking", "reply"],
      mirrorToFooter: false,
    });
    return false;
  }
}

els.voiceOrb?.addEventListener("click", handleVoiceTap);
els.navVoice?.addEventListener("click", handleVoiceTap);
els.statusShortcut?.addEventListener("click", () => {
  window.location.hash = "status";
});
els.settingsShortcut?.addEventListener("click", () => {
  window.location.hash = "settings";
});
els.deviceDetailBack?.addEventListener("click", () => {
  window.location.hash = "devices";
});
els.deviceActionOn?.addEventListener("click", () => {
  void runSelectedDeviceAction("on");
});
els.deviceActionOff?.addEventListener("click", () => {
  void runSelectedDeviceAction("off");
});
els.deviceActionQuery?.addEventListener("click", () => {
  void runSelectedDeviceAction("query");
});
els.settingsMicTest?.addEventListener("click", () => {
  void testMicrophonePermission();
});
els.settingsInstallApp?.addEventListener("click", () => {
  void promptInstallApp();
});
els.settingsDemoToggle?.addEventListener("click", () => {
  setDemoMode(!state.demoMode);
});
els.settingsApiForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  void saveApiBaseFromSettings();
});
els.settingsApiTest?.addEventListener("click", () => {
  void testApiBaseFromSettings();
});
els.settingsApiReset?.addEventListener("click", () => {
  void resetApiBaseSettings();
});
els.settingsRefreshDiagnostics?.addEventListener("click", () => {
  void refreshDiagnostics();
});
els.phoneWakeStart?.addEventListener("click", startPhoneWakeMode);
els.phoneWakeStop?.addEventListener("click", stopPhoneWakeMode);
els.boardWakeStart?.addEventListener("click", async () => {
  setText(els.boardWakeStatus, "กำลังสั่งบอร์ด...");
  try {
    await queueVoiceNodeWakeCommand("start");
  } catch (error) {
    setText(els.boardWakeStatus, "สั่งบอร์ดไม่สำเร็จ");
  }
});
els.boardWakeStop?.addEventListener("click", async () => {
  setText(els.boardWakeStatus, "กำลังหยุดบอร์ด...");
  try {
    await queueVoiceNodeWakeCommand("stop");
  } catch (error) {
    setText(els.boardWakeStatus, "หยุดบอร์ดไม่สำเร็จ");
  }
});

els.lightToggle?.addEventListener("click", async () => {
  if (!state.deviceOnline) {
    setText(els.lightState, "บอร์ดยัง offline");
    return;
  }
  const nextAction = state.lightOn ? "ปิดไฟห้องนั่งเล่น" : "เปิดไฟห้องนั่งเล่น";
  els.lightToggle.disabled = true;
  try {
    await sendChatMessage(nextAction, { statusText: "กำลังส่งคำสั่งอุปกรณ์..." });
  } catch (error) {
    setText(els.lightState, "ส่งคำสั่งไม่สำเร็จ");
  } finally {
    els.lightToggle.disabled = false;
  }
});

els.chatForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = els.chatInput?.value || "";
  if (!message.trim()) {
    return;
  }
  if (els.chatInput) {
    els.chatInput.value = "";
  }
  try {
    await sendChatMessage(message, { statusText: "กำลังถามน้องฟ้า..." });
  } catch (error) {
    setText(els.chatReply, "ส่งข้อความไม่สำเร็จ");
  }
});

window.addEventListener("beforeunload", () => {
  window.clearTimeout(state.recordingTimeout);
  stopVoiceRecognition({ resetBusy: true });
  stopPhoneWakeMode();
  stopMediaStream();
});

window.addEventListener("hashchange", routeFromLocation);

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  state.deferredInstallPrompt = event;
  updateInstallUi();
  void refreshDiagnostics();
});

window.addEventListener("appinstalled", () => {
  state.deferredInstallPrompt = null;
  state.appInstalled = true;
  updateInstallUi();
  void refreshDiagnostics();
});

if (window.lucide) {
  window.lucide.createIcons();
}

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/mobile-service-worker.js").catch(() => {});
  });
}

updateChatStatus({
  title: "พร้อมรับคำสั่ง",
  detail: "พิมพ์หรือพูดกับน้องฟ้าได้เลย",
  label: "พร้อม",
  tone: "neutral",
  activeStep: "input",
  completedSteps: [],
  mirrorToFooter: false,
});
setVoiceTranscript("", "neutral");
updateSettingsUi();

const initialAction = new URLSearchParams(window.location.search).get("action");
if (initialAction === "voice") {
  window.location.hash = "wake";
}
routeFromLocation();
updatePhoneWakeUi();
refreshAllStatus();
window.setInterval(refreshAllStatus, 15000);
