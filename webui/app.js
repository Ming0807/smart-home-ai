const chatHistory = document.getElementById("chat-history");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatLoading = document.getElementById("chat-loading");
const chatStatus = document.getElementById("chat-status");
const chatSendButton = document.getElementById("chat-send-button");
const chatMicButton = document.getElementById("chat-mic-button");
const chatStopButton = document.getElementById("chat-stop-button");
const chatMicStatus = document.getElementById("chat-mic-status");
const chatHeardText = document.getElementById("chat-heard-text");
const voiceTurnStatus = document.getElementById("voice-turn-status");
const quickActions = document.getElementById("quick-actions");
const exitQuickActions = document.getElementById("exit-quick-actions");
const micStateIndicator = document.getElementById("mic-state-indicator");
const keepMicIndicator = document.getElementById("keep-mic-indicator");
const pirSimToggle = document.getElementById("pir-sim-toggle");

const sensorTemperature = document.getElementById("sensor-temperature");
const sensorHumidity = document.getElementById("sensor-humidity");
const sensorFreshness = document.getElementById("sensor-freshness");
const sensorUpdated = document.getElementById("sensor-updated");
const sensorDeviceId = document.getElementById("sensor-device-id");

const motionStatus = document.getElementById("motion-status");
const motionLastDetected = document.getElementById("motion-last-detected");
const motionLastEvent = document.getElementById("motion-last-event");
const motionGreeting = document.getElementById("motion-greeting");

const deviceOnlineIndicator = document.getElementById("device-online-indicator");
const deviceLatestCommand = document.getElementById("device-latest-command");
const devicePendingCount = document.getElementById("device-pending-count");
const deviceLastSeen = document.getElementById("device-last-seen");

const voiceModeIndicator = document.getElementById("voice-mode-indicator");
const voiceProvider = document.getElementById("voice-provider");
const voiceName = document.getElementById("voice-name");
const voiceOutputFile = document.getElementById("voice-output-file");

const ttsForm = document.getElementById("tts-form");
const ttsInput = document.getElementById("tts-input");
const ttsSubmitButton = document.getElementById("tts-submit-button");
const ttsAudioPlayer = document.getElementById("tts-audio-player");
const ttsStatusText = document.getElementById("tts-status-text");
const voiceDebugStatus = document.getElementById("voice-debug-status");

const weatherForm = document.getElementById("weather-form");
const weatherLocation = document.getElementById("weather-location");
const weatherResult = document.getElementById("weather-result");
const weatherSubmitButton = document.getElementById("weather-submit-button");

const refreshAllButton = document.getElementById("refresh-all-button");
const sensorRefreshButton = document.getElementById("sensor-refresh-button");
const motionRefreshButton = document.getElementById("motion-refresh-button");
const relayOnButton = document.getElementById("relay-on-button");
const relayOffButton = document.getElementById("relay-off-button");

const SpeechRecognitionConstructor =
  window.SpeechRecognition || window.webkitSpeechRecognition || null;

const state = {
  chatBusy: false,
  recording: false,
  speechRecognition: null,
  mediaRecorder: null,
  mediaStream: null,
  audioChunks: [],
  maxChatHistoryItems: 50,
  keepMicOpen: false,
  stopRequested: false,
  autoListenTimerId: null,
  pirTouched: false,
};

function formatDate(value) {
  if (!value) {
    return "-";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString("th-TH", {
    dateStyle: "short",
    timeStyle: "medium",
  });
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function setPillState(element, tone, text) {
  element.className = `status-pill ${tone}`;
  element.textContent = text;
}

function setMicStatus(message, tone = "neutral") {
  chatMicStatus.hidden = false;
  chatMicStatus.textContent = message;
  chatMicStatus.classList.remove("chat-mic-status-live", "chat-mic-status-busy");
  if (tone === "live") {
    chatMicStatus.classList.add("chat-mic-status-live");
  } else if (tone === "busy") {
    chatMicStatus.classList.add("chat-mic-status-busy");
  }
}

function showHeardText(text) {
  if (!text) {
    chatHeardText.hidden = true;
    chatHeardText.textContent = "";
    return;
  }

  chatHeardText.hidden = false;
  chatHeardText.textContent = `ได้ยินว่า: ${text}`;
}

function setMicState(mode) {
  if (mode === "listening") {
    setPillState(micStateIndicator, "good", "Listening");
    return;
  }
  if (mode === "thinking") {
    setPillState(micStateIndicator, "warn", "Thinking");
    return;
  }
  setPillState(micStateIndicator, "neutral", "Closed");
}

function setKeepMicIndicator(keepOpen, reason = "") {
  state.keepMicOpen = keepOpen;
  if (keepOpen) {
    setPillState(keepMicIndicator, "good", "keep_mic_open: true");
    voiceTurnStatus.textContent = reason || "AI ขอเปิดไมค์ต่อเพื่อคุยต่อเนื่อง";
    return;
  }
  setPillState(keepMicIndicator, "neutral", "keep_mic_open: false");
  if (reason) {
    voiceTurnStatus.textContent = reason;
  }
}

function currentPirState() {
  return pirSimToggle.checked ? 1 : 0;
}

function clearAutoListenTimer() {
  if (state.autoListenTimerId !== null) {
    window.clearTimeout(state.autoListenTimerId);
    state.autoListenTimerId = null;
  }
}

function getChatActionButtons() {
  return [
    chatSendButton,
    chatMicButton,
    chatStopButton,
    weatherSubmitButton,
    relayOnButton,
    relayOffButton,
    ...quickActions.querySelectorAll("button[data-message]"),
    ...exitQuickActions.querySelectorAll("button[data-exit-message]"),
  ];
}

function setChatBusy(isBusy) {
  state.chatBusy = isBusy;
  const controlsDisabled = isBusy || state.recording;

  chatInput.disabled = controlsDisabled;
  pirSimToggle.disabled = isBusy;

  for (const button of getChatActionButtons()) {
    if ((button === chatMicButton || button === chatStopButton) && state.recording) {
      button.disabled = false;
      continue;
    }
    if (button === chatStopButton) {
      button.disabled = !state.recording && !state.keepMicOpen;
      continue;
    }
    button.disabled = controlsDisabled;
  }

  chatLoading.hidden = !isBusy;

  if (isBusy) {
    setPillState(chatStatus, "warn", "กำลังประมวลผล");
  } else if (state.recording) {
    setPillState(chatStatus, "warn", "กำลังฟังเสียง");
  } else if (!navigator.onLine) {
    setPillState(chatStatus, "bad", "ออฟไลน์");
  } else {
    setPillState(chatStatus, "neutral", "พร้อมใช้งาน");
  }
}

function revokeAudioObjectUrl(audioElement) {
  const previousUrl = audioElement.dataset.objectUrl;
  if (previousUrl) {
    URL.revokeObjectURL(previousUrl);
    delete audioElement.dataset.objectUrl;
  }
}

function trimChatHistory() {
  while (chatHistory.children.length > state.maxChatHistoryItems) {
    const oldest = chatHistory.firstElementChild;
    if (!oldest) {
      return;
    }
    for (const audioElement of oldest.querySelectorAll("audio")) {
      revokeAudioObjectUrl(audioElement);
    }
    oldest.remove();
  }
}

function attachAudioBlob(audioElement, blobUrl) {
  revokeAudioObjectUrl(audioElement);
  audioElement.dataset.objectUrl = blobUrl;
  audioElement.src = blobUrl;
  audioElement.load();
}

async function fetchJson(url, options = {}, timeoutMs = 30000) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      cache: "no-store",
      ...options,
      signal: controller.signal,
    });
    const text = await response.text();
    const data = text ? JSON.parse(text) : {};
    return { response, data };
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function requestSpeechAudioUrl(text) {
  const { response, data } = await fetchJson(
    "/voice/speak",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    },
    40000
  );

  if (!response.ok || data.status !== "ok" || !data.audio_url) {
    throw new Error(data.error || "tts request failed");
  }

  return data.audio_url;
}

function getAudioToken(url) {
  try {
    const resolvedUrl = new URL(url, window.location.origin);
    return resolvedUrl.searchParams.get("token");
  } catch (error) {
    return null;
  }
}

async function ensureAudioTokenReady(url) {
  const token = getAudioToken(url);
  if (!token) {
    return;
  }

  const { response, data } = await fetchJson("/voice/status", {}, 8000);
  if (!response.ok) {
    throw new Error("voice status failed");
  }
  if (data.current_token && data.current_token !== token) {
    throw new Error("audio superseded");
  }
  if (!data.audio_ready) {
    throw new Error("audio not ready");
  }
}

async function fetchAudioBlobUrl(url) {
  const bustUrl = `${url}${url.includes("?") ? "&" : "?"}v=${Date.now()}`;
  const response = await fetch(bustUrl, {
    cache: "no-store",
    headers: { Accept: "audio/mpeg" },
  });

  if (!response.ok) {
    throw new Error(`audio request failed: ${response.status}`);
  }

  const audioBlob = await response.blob();
  if (!audioBlob.size) {
    throw new Error("audio blob is empty");
  }
  return URL.createObjectURL(audioBlob);
}

async function loadAudioWithRetry(
  audioElement,
  url,
  autoplay = false,
  statusElement = null,
  attempt = 0,
  recoveryText = null
) {
  const maxAttempts = 24;
  if (statusElement) {
    statusElement.textContent = `กำลังเตรียมเสียง... (${attempt + 1}/${maxAttempts})`;
  }

  try {
    await ensureAudioTokenReady(url);
    const blobUrl = await fetchAudioBlobUrl(url);
    attachAudioBlob(audioElement, blobUrl);

    await new Promise((resolve, reject) => {
      const onLoaded = () => {
        cleanup();
        resolve();
      };
      const onError = () => {
        cleanup();
        reject(new Error("audio not playable"));
      };
      const cleanup = () => {
        audioElement.removeEventListener("canplaythrough", onLoaded);
        audioElement.removeEventListener("error", onError);
      };

      audioElement.addEventListener("canplaythrough", onLoaded, { once: true });
      audioElement.addEventListener("error", onError, { once: true });
    });

    if (statusElement) {
      statusElement.textContent = autoplay ? "เสียงพร้อมแล้ว กำลังเล่น..." : "เสียงพร้อมแล้ว";
    }

    if (autoplay) {
      await audioElement.play().catch(() => {});
      if (statusElement) {
        statusElement.textContent = "เล่นเสียงอัตโนมัติแล้ว";
      }
    }
  } catch (error) {
    const isSuperseded = error instanceof Error && error.message === "audio superseded";
    if (isSuperseded) {
      if (statusElement) {
        statusElement.textContent = "มีคำตอบใหม่กว่า ข้ามเสียงนี้";
      }
      return;
    }

    if (attempt < maxAttempts - 1) {
      await sleep(750);
      return loadAudioWithRetry(
        audioElement,
        url,
        autoplay,
        statusElement,
        attempt + 1,
        recoveryText
      );
    }

    if (recoveryText) {
      try {
        const regeneratedAudioUrl = await requestSpeechAudioUrl(recoveryText);
        return loadAudioWithRetry(audioElement, regeneratedAudioUrl, autoplay, statusElement, 0, null);
      } catch (recoveryError) {
        // Final error state below.
      }
    }

    if (statusElement) {
      statusElement.textContent = "ยังสร้างเสียงไม่สำเร็จ ลองใหม่อีกครั้งได้";
    }
  }
}

function appendMessage(role, text, meta = {}) {
  const wrapper = document.createElement("article");
  wrapper.className = `message ${role}`;

  const header = document.createElement("div");
  header.className = "message-header";

  const roleLabel = document.createElement("span");
  roleLabel.className = "message-role";
  roleLabel.textContent = role === "user" ? "คุณ" : "AI";

  const timeLabel = document.createElement("span");
  timeLabel.className = "message-time";
  timeLabel.textContent = new Date().toLocaleTimeString("th-TH", {
    hour: "2-digit",
    minute: "2-digit",
  });

  header.append(roleLabel, timeLabel);

  const body = document.createElement("p");
  body.className = "message-text";
  body.textContent = text;
  wrapper.append(header, body);

  if (meta.intent || meta.source || meta.action) {
    const metaRow = document.createElement("div");
    metaRow.className = "message-meta";

    for (const [key, value] of [
      ["intent", meta.intent],
      ["source", meta.source],
      ["action", meta.action],
    ]) {
      if (!value) {
        continue;
      }
      const badge = document.createElement("span");
      badge.className = "badge";
      badge.textContent = `${key}: ${value}`;
      metaRow.appendChild(badge);
    }

    if (typeof meta.keepMicOpen === "boolean") {
      const keepBadge = document.createElement("span");
      keepBadge.className = "badge";
      keepBadge.textContent = `keep_mic_open: ${meta.keepMicOpen ? "true" : "false"}`;
      metaRow.appendChild(keepBadge);
    }

    wrapper.appendChild(metaRow);
  }

  let audioElement = null;
  let audioPromise = Promise.resolve();
  if (meta.audioUrl) {
    audioElement = document.createElement("audio");
    audioElement.controls = true;
    audioElement.preload = "metadata";

    const audioStatus = document.createElement("p");
    audioStatus.className = "audio-status";
    audioStatus.textContent = "กำลังเตรียมเสียง...";

    wrapper.append(audioElement, audioStatus);
    audioPromise = loadAudioWithRetry(audioElement, meta.audioUrl, true, audioStatus, 0, text);
  }

  chatHistory.appendChild(wrapper);
  trimChatHistory();
  chatHistory.scrollTop = chatHistory.scrollHeight;
  return { wrapper, audioElement, audioPromise };
}

async function refreshVoiceDebugStatus() {
  try {
    const { response, data } = await fetchJson("/voice/status", {}, 8000);
    if (!response.ok) {
      throw new Error("voice status failed");
    }

    const parts = [
      `ready: ${data.audio_ready ? "yes" : "no"}`,
      `size: ${data.file_size_bytes || 0} bytes`,
    ];
    if (data.current_token) {
      parts.push(`token: ${data.current_token.slice(0, 8)}`);
    }
    if (data.last_generated_at) {
      parts.push(`updated: ${formatDate(data.last_generated_at)}`);
    }
    if (data.last_error) {
      parts.push(`error: ${data.last_error}`);
    }
    voiceDebugStatus.textContent = parts.join(" | ");
  } catch (error) {
    voiceDebugStatus.textContent = "อ่านสถานะเสียงไม่สำเร็จ";
  }
}

function getReadableErrorMessage(error, fallbackText) {
  if (error && error.name === "AbortError") {
    return "คำขอนี้ใช้เวลานานเกินไป ลองใหม่อีกครั้งได้";
  }
  if (error instanceof TypeError) {
    return "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ ลองเช็กว่า backend ยังทำงานอยู่";
  }
  if (error instanceof SyntaxError) {
    return "เซิร์ฟเวอร์ตอบกลับมาไม่สมบูรณ์";
  }
  return error instanceof Error && error.message ? error.message : fallbackText;
}

function formatHeartbeatStatus(lastHeartbeatAt, secondsSinceHeartbeat) {
  if (!lastHeartbeatAt) {
    return "-";
  }
  const formattedTime = formatDate(lastHeartbeatAt);
  if (secondsSinceHeartbeat === null || secondsSinceHeartbeat === undefined) {
    return formattedTime;
  }
  return `${formattedTime} (${secondsSinceHeartbeat} วินาทีก่อน)`;
}

function browserSupportsRecording() {
  return Boolean(window.MediaRecorder && navigator.mediaDevices?.getUserMedia);
}

function browserSupportsSpeechRecognition() {
  return Boolean(SpeechRecognitionConstructor);
}

function createSpeechRecognition() {
  if (!SpeechRecognitionConstructor) {
    return null;
  }
  const recognition = new SpeechRecognitionConstructor();
  recognition.lang = "th-TH";
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  return recognition;
}

function getSupportedRecordingMimeType() {
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4",
  ];
  for (const candidate of candidates) {
    if (window.MediaRecorder && MediaRecorder.isTypeSupported(candidate)) {
      return candidate;
    }
  }
  return "";
}

function cleanupMediaStream() {
  if (state.mediaStream) {
    for (const track of state.mediaStream.getTracks()) {
      track.stop();
    }
  }
  state.mediaStream = null;
  state.mediaRecorder = null;
  state.audioChunks = [];
}

async function waitForAssistantPlayback(entry) {
  if (!entry) {
    await sleep(400);
    return;
  }

  await entry.audioPromise.catch(() => {});
  const audioElement = entry.audioElement;
  if (!audioElement) {
    await sleep(400);
    return;
  }

  if (audioElement.paused) {
    await sleep(400);
    return;
  }

  await new Promise((resolve) => {
    const finish = () => {
      cleanup();
      resolve();
    };
    const cleanup = () => {
      audioElement.removeEventListener("ended", finish);
      audioElement.removeEventListener("error", finish);
      window.clearTimeout(timeoutId);
    };
    const timeoutId = window.setTimeout(finish, 12000);
    audioElement.addEventListener("ended", finish, { once: true });
    audioElement.addEventListener("error", finish, { once: true });
  });
}

function normalizeVoicePayload(payload) {
  if (payload && payload.data) {
    return payload.data;
  }
  return payload;
}

async function refreshDashboardStatus() {
  try {
    const { response, data } = await fetchJson("/dashboard/status", {}, 10000);
    if (!response.ok) {
      throw new Error("dashboard status failed");
    }

    let esp32Status = {
      device_id: data.device.device_id,
      online: data.device.online,
      last_seen_at: data.device.last_seen_at,
      seconds_since_heartbeat: data.device.seconds_since_heartbeat,
      pending_command_count: data.device.pending_command_count,
      latest_command: data.device.latest_command,
    };

    try {
      const encodedDeviceId = encodeURIComponent(data.device.device_id || data.sensor.device_id || "esp32-01");
      const statusResult = await fetchJson(`/esp32/status?device_id=${encodedDeviceId}`, {}, 10000);
      if (statusResult.response.ok) {
        esp32Status = statusResult.data;
      }
    } catch (statusError) {
      // Keep aggregate state.
    }

    state.maxChatHistoryItems =
      Number.isFinite(data.app?.max_chat_history_items) && data.app.max_chat_history_items > 0
        ? data.app.max_chat_history_items
        : state.maxChatHistoryItems;
    trimChatHistory();

    sensorDeviceId.textContent = data.sensor.device_id || "-";
    sensorTemperature.textContent =
      data.sensor.temperature === null ? "-" : `${Math.round(data.sensor.temperature)} °C`;
    sensorHumidity.textContent =
      data.sensor.humidity === null ? "-" : `${Math.round(data.sensor.humidity)} %`;
    sensorFreshness.textContent = data.sensor.is_fresh ? "ข้อมูลล่าสุดพร้อมใช้งาน" : "ยังไม่มีข้อมูลใหม่";
    sensorUpdated.textContent = formatDate(data.sensor.received_at || data.sensor.timestamp);

    motionStatus.textContent = data.motion.motion_detected ? "พบการเคลื่อนไหว" : "ยังไม่พบการเคลื่อนไหว";
    motionLastDetected.textContent = formatDate(data.motion.last_motion_at);
    motionLastEvent.textContent = formatDate(data.motion.last_event_at);
    motionGreeting.textContent = data.motion.greeting_message || "-";

    if (!state.pirTouched) {
      pirSimToggle.checked = Boolean(data.motion.motion_detected);
    }

    setPillState(
      deviceOnlineIndicator,
      esp32Status.online ? "good" : "warn",
      esp32Status.online ? "ESP32 online" : "ESP32 offline"
    );
    deviceLatestCommand.textContent = esp32Status.latest_command
      ? `relay ch${esp32Status.latest_command.channel} -> ${esp32Status.latest_command.action}`
      : "-";
    devicePendingCount.textContent = String(esp32Status.pending_command_count ?? 0);
    deviceLastSeen.textContent = formatHeartbeatStatus(
      esp32Status.last_seen_at,
      esp32Status.seconds_since_heartbeat
    );

    voiceProvider.textContent = data.voice.provider || "-";
    voiceName.textContent = data.voice.default_voice || "-";
    voiceOutputFile.textContent = data.voice.output_file || "-";

    if (data.voice.tts_enabled && data.voice.demo_voice_mode) {
      setPillState(voiceModeIndicator, "good", "Demo voice mode เปิดอยู่");
    } else if (data.voice.tts_enabled) {
      setPillState(voiceModeIndicator, "warn", "TTS เปิดอยู่ แต่ demo voice ปิด");
    } else {
      setPillState(voiceModeIndicator, "bad", "TTS ปิดอยู่");
    }
  } catch (error) {
    sensorFreshness.textContent = "ดึงสถานะไม่สำเร็จ";
    motionStatus.textContent = "ดึงสถานะไม่สำเร็จ";
    motionLastDetected.textContent = "-";
    motionLastEvent.textContent = "-";
    motionGreeting.textContent = "-";
    setPillState(deviceOnlineIndicator, "bad", "อ่านสถานะไม่ได้");
    setPillState(voiceModeIndicator, "bad", "อ่านสถานะไม่ได้");
  }
}

async function ensureChatAudioUrl(replyText, audioUrl) {
  if (audioUrl) {
    return audioUrl;
  }
  if (!replyText || !replyText.trim()) {
    return null;
  }
  return requestSpeechAudioUrl(replyText.trim());
}

async function handleChatResponse(data, options = {}) {
  const { appendUserMessage = true, userMessage = "", heardText = "", refreshStatus = true } = options;
  const userText = heardText || userMessage;
  if (appendUserMessage && userText) {
    appendMessage("user", userText);
  }
  if (heardText) {
    showHeardText(heardText);
  } else if (!userMessage) {
    showHeardText("");
  }

  let resolvedAudioUrl = null;
  try {
    resolvedAudioUrl = await ensureChatAudioUrl(data.reply, data.audio_url || null);
  } catch (error) {
    resolvedAudioUrl = null;
  }

  const assistantEntry = appendMessage("assistant", data.reply, {
    intent: data.intent,
    source: data.source,
    audioUrl: resolvedAudioUrl,
  });

  setPillState(chatStatus, "good", "ตอบแล้ว");
  if (data.intent === "weather_query") {
    weatherResult.textContent = data.reply;
    weatherResult.classList.remove("muted");
  }
  if (refreshStatus) {
    await refreshDashboardStatus();
    await refreshVoiceDebugStatus();
  }
  return assistantEntry;
}

async function maybeContinueListening(assistantEntry) {
  clearAutoListenTimer();
  if (!state.keepMicOpen || state.stopRequested) {
    setMicState("closed");
    return;
  }

  await waitForAssistantPlayback(assistantEntry);
  if (!state.keepMicOpen || state.stopRequested || state.recording || state.chatBusy) {
    setMicState("closed");
    return;
  }

  voiceTurnStatus.textContent = "กำลังเปิดไมค์ต่ออัตโนมัติ...";
  state.autoListenTimerId = window.setTimeout(() => {
    state.autoListenTimerId = null;
    startVoiceRecording();
  }, 350);
}

async function handleVoiceTurnResponse(payload, options = {}) {
  const data = normalizeVoicePayload(payload);
  const { appendUserMessage = true } = options;

  if (data.heard_text) {
    showHeardText(data.heard_text);
  }

  const assistantEntry = appendMessage("assistant", data.reply, {
    intent: data.intent,
    source: data.source,
    action: data.action,
    keepMicOpen: data.keep_mic_open,
    audioUrl: data.audio_url || null,
  });

  if (appendUserMessage && data.heard_text) {
    chatHistory.insertBefore(appendMessage("user", data.heard_text).wrapper, assistantEntry.wrapper);
  }

  setKeepMicIndicator(Boolean(data.keep_mic_open), data.keep_mic_open ? "AI อยากคุยต่อ" : "AI ปิดไมค์หลังตอบรอบนี้");
  setPillState(chatStatus, "good", "ตอบแล้ว");

  await refreshDashboardStatus();
  await refreshVoiceDebugStatus();
  void maybeContinueListening(assistantEntry);
}

async function sendChatMessage(message) {
  const trimmed = message.trim();
  if (!trimmed || state.chatBusy || state.recording) {
    return;
  }

  appendMessage("user", trimmed);
  chatInput.value = "";
  showHeardText("");
  setChatBusy(true);
  state.stopRequested = true;
  setKeepMicIndicator(false, "โหมดแชตข้อความปิดไมค์ต่อเนื่องไว้ก่อน");

  try {
    const { response, data } = await fetchJson(
      "/chat",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: trimmed }),
      },
      45000
    );

    if (!response.ok) {
      throw new Error(data.detail || "ส่งข้อความไม่สำเร็จ");
    }

    await handleChatResponse(data, { appendUserMessage: false, userMessage: trimmed });
  } catch (error) {
    appendMessage("assistant", getReadableErrorMessage(error, "เกิดปัญหาระหว่างส่งข้อความ ลองใหม่อีกครั้งได้ไหม"), {
      source: "fallback",
    });
    setPillState(chatStatus, "bad", "เกิดข้อผิดพลาด");
  } finally {
    setChatBusy(false);
    setMicState("closed");
  }
}

async function sendVoiceText(message) {
  const trimmed = message.trim();
  if (!trimmed || state.chatBusy) {
    return;
  }

  clearAutoListenTimer();
  setChatBusy(true);
  setMicState("thinking");
  setMicStatus("กำลังส่งข้อความเสียงเข้า voice chat...", "busy");

  const formData = new FormData();
  formData.append("message", trimmed);
  formData.append("pir_state", String(currentPirState()));

  try {
    const { response, data } = await fetchJson(
      "/voice/chat",
      {
        method: "POST",
        body: formData,
      },
      60000
    );

    if (!response.ok) {
      throw new Error(data.detail || "ส่งข้อความเสียงไม่สำเร็จ");
    }

    await handleVoiceTurnResponse(data);
    setMicStatus("ตอบกลับด้วยเสียงแล้ว", "busy");
  } catch (error) {
    const messageText = getReadableErrorMessage(error, "เกิดปัญหาระหว่างส่งข้อความเสียง ลองใหม่อีกครั้งได้ไหม");
    appendMessage("assistant", messageText, { source: "fallback" });
    setPillState(chatStatus, "bad", "เกิดข้อผิดพลาด");
    setKeepMicIndicator(false, "ปิดไมค์ต่อเนื่องชั่วคราวเพราะเกิดข้อผิดพลาด");
    setMicStatus(messageText, "busy");
  } finally {
    setChatBusy(false);
    if (!state.recording) {
      setMicState(state.keepMicOpen ? "listening" : "closed");
    }
  }
}

async function sendVoiceRecording(audioBlob, mimeType) {
  if (!audioBlob.size) {
    setMicStatus("ไม่ได้รับข้อมูลเสียง ลองกดไมค์ใหม่อีกครั้ง", "busy");
    return;
  }

  setChatBusy(true);
  setMicState("thinking");
  setMicStatus("กำลังแปลงเสียงเป็นข้อความ...", "busy");
  showHeardText("");

  const extension = mimeType.includes("ogg") ? "ogg" : mimeType.includes("mp4") ? "m4a" : "webm";
  const formData = new FormData();
  formData.append("audio", audioBlob, `voice-input.${extension}`);
  formData.append("pir_state", String(currentPirState()));

  try {
    const { response, data } = await fetchJson(
      "/voice/chat",
      {
        method: "POST",
        body: formData,
      },
      120000
    );

    if (!response.ok) {
      throw new Error(data.detail || "ส่งเสียงไม่สำเร็จ");
    }

    await handleVoiceTurnResponse(data);
    setMicStatus("ตอบกลับด้วยเสียงแล้ว", "busy");
  } catch (error) {
    const messageText = getReadableErrorMessage(error, "เกิดปัญหาระหว่างส่งเสียง ลองใหม่อีกครั้งได้ไหม");
    appendMessage("assistant", messageText, { source: "fallback" });
    setPillState(chatStatus, "bad", "เกิดข้อผิดพลาด");
    setKeepMicIndicator(false, "ปิดไมค์ต่อเนื่องชั่วคราวเพราะเกิดข้อผิดพลาด");
    setMicStatus(messageText, "busy");
  } finally {
    setChatBusy(false);
    if (!state.recording) {
      setMicState(state.keepMicOpen ? "listening" : "closed");
    }
  }
}

async function startBrowserSpeechRecognition() {
  const recognition = createSpeechRecognition();
  if (!recognition) {
    return false;
  }

  try {
    state.speechRecognition = recognition;
    state.recording = true;
    chatMicButton.textContent = "หยุดฟัง";
    setMicState("listening");
    setMicStatus("กำลังฟังผ่านเบราว์เซอร์ พูดได้เลย", "live");
    setChatBusy(false);

    recognition.onresult = async (event) => {
      const transcript = Array.from(event.results || [])
        .map((result) => result[0]?.transcript || "")
        .join(" ")
        .trim();

      state.recording = false;
      state.speechRecognition = null;
      chatMicButton.textContent = "ไมค์";
      setChatBusy(false);
      await sendVoiceText(transcript);
    };

    recognition.onerror = (event) => {
      state.recording = false;
      state.speechRecognition = null;
      chatMicButton.textContent = "ไมค์";
      setChatBusy(false);
      setKeepMicIndicator(false, "เบราว์เซอร์ฟังเสียงไม่สำเร็จ");
      setMicState("closed");

      if (event.error === "no-speech") {
        setMicStatus("ไม่ได้ยินเสียงชัดพอ ลองพูดใหม่อีกครั้งได้", "busy");
        return;
      }
      if (event.error === "not-allowed") {
        setMicStatus("เบราว์เซอร์ยังไม่ได้รับสิทธิ์ไมโครโฟน ลองอนุญาตก่อน", "busy");
        return;
      }
      setMicStatus("เบราว์เซอร์ฟังเสียงไม่สำเร็จ จะสลับไปใช้อัปโหลดเสียงแทน", "busy");
    };

    recognition.onend = () => {
      if (!state.recording) {
        return;
      }
      state.recording = false;
      state.speechRecognition = null;
      chatMicButton.textContent = "ไมค์";
      setChatBusy(false);
      setMicState("closed");
      setMicStatus("หยุดฟังแล้ว ลองกดไมค์ใหม่อีกครั้งได้", "busy");
    };

    recognition.start();
    return true;
  } catch (error) {
    state.recording = false;
    state.speechRecognition = null;
    chatMicButton.textContent = "ไมค์";
    setChatBusy(false);
    setMicState("closed");
    setMicStatus("เปิดโหมดฟังเสียงในเบราว์เซอร์ไม่สำเร็จ จะใช้อัปโหลดเสียงแทน", "busy");
    return false;
  }
}

async function startVoiceRecording() {
  if (state.chatBusy || state.recording) {
    return;
  }

  clearAutoListenTimer();
  state.stopRequested = false;

  if (browserSupportsSpeechRecognition()) {
    const startedBrowserRecognition = await startBrowserSpeechRecognition();
    if (startedBrowserRecognition) {
      return;
    }
  }

  if (!browserSupportsRecording()) {
    setMicStatus("เบราว์เซอร์นี้ยังไม่รองรับการอัดเสียงสำหรับเดโมนี้", "busy");
    return;
  }

  const mimeType = getSupportedRecordingMimeType();
  if (!mimeType) {
    setMicStatus("เบราว์เซอร์นี้ยังไม่รองรับรูปแบบไฟล์เสียงที่ใช้งานได้", "busy");
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });

    state.mediaStream = stream;
    state.audioChunks = [];
    state.mediaRecorder = new MediaRecorder(stream, { mimeType });

    state.mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data && event.data.size > 0) {
        state.audioChunks.push(event.data);
      }
    });

    state.mediaRecorder.addEventListener("stop", async () => {
      const recordedBlob = new Blob(state.audioChunks, { type: mimeType });
      cleanupMediaStream();
      state.recording = false;
      chatMicButton.textContent = "ไมค์";
      setChatBusy(false);
      await sendVoiceRecording(recordedBlob, mimeType);
    });

    state.recording = true;
    chatMicButton.textContent = "หยุดอัด";
    setMicState("listening");
    setMicStatus("กำลังอัดเสียงอยู่ กดหยุดเมื่อพูดจบ", "live");
    setChatBusy(false);
    state.mediaRecorder.start();
  } catch (error) {
    cleanupMediaStream();
    state.recording = false;
    chatMicButton.textContent = "ไมค์";
    setChatBusy(false);
    setMicState("closed");
    setMicStatus(
      getReadableErrorMessage(error, "เปิดไมโครโฟนไม่สำเร็จ ลองเช็ก permission ของเบราว์เซอร์"),
      "busy"
    );
  }
}

function stopVoiceRecording() {
  if (!state.recording) {
    return;
  }

  if (state.speechRecognition) {
    setMicStatus("หยุดฟังแล้ว กำลังสรุปคำพูด...", "busy");
    state.speechRecognition.abort();
    state.speechRecognition = null;
    state.recording = false;
    chatMicButton.textContent = "ไมค์";
    setChatBusy(false);
    setMicState("thinking");
    return;
  }

  if (!state.mediaRecorder) {
    return;
  }

  setMicStatus("หยุดอัดแล้ว กำลังเตรียมส่งเสียง...", "busy");
  if (state.mediaRecorder.state !== "inactive") {
    state.mediaRecorder.stop();
  }
  setMicState("thinking");
}

function stopContinuousConversation() {
  state.stopRequested = true;
  clearAutoListenTimer();
  setKeepMicIndicator(false, "ปิดไมค์ต่อเนื่องแล้ว");
  if (state.recording) {
    stopVoiceRecording();
  } else {
    setMicState("closed");
    setMicStatus("หยุดฟังแล้ว กดไมค์เมื่ออยากเริ่มใหม่", "busy");
  }
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await sendChatMessage(chatInput.value);
});

chatMicButton.addEventListener("click", async () => {
  if (state.recording) {
    stopVoiceRecording();
    return;
  }
  await startVoiceRecording();
});

chatStopButton.addEventListener("click", () => {
  stopContinuousConversation();
});

quickActions.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-message]");
  if (!button || button.disabled) {
    return;
  }
  await sendChatMessage(button.dataset.message || "");
});

exitQuickActions.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-exit-message]");
  if (!button || button.disabled) {
    return;
  }
  await sendVoiceText(button.dataset.exitMessage || "");
});

pirSimToggle.addEventListener("change", () => {
  state.pirTouched = true;
  voiceTurnStatus.textContent = pirSimToggle.checked
    ? "PIR จำลอง: มีคนอยู่ ระบบพร้อมเปิดไมค์ต่อเมื่อเหมาะสม"
    : "PIR จำลอง: ไม่มีคนอยู่ ระบบจะเคารพคำตัดสินของ AI มากขึ้น";
});

sensorRefreshButton.addEventListener("click", refreshDashboardStatus);
motionRefreshButton.addEventListener("click", refreshDashboardStatus);
refreshAllButton.addEventListener("click", async () => {
  await refreshDashboardStatus();
  await refreshVoiceDebugStatus();
});

relayOnButton.addEventListener("click", async () => {
  await sendChatMessage("เปิดไฟ");
});

relayOffButton.addEventListener("click", async () => {
  await sendChatMessage("ปิดไฟ");
});

ttsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = ttsInput.value.trim();
  if (!text) {
    ttsStatusText.textContent = "กรุณาใส่ข้อความก่อน";
    return;
  }

  ttsStatusText.textContent = "กำลังสร้างเสียง...";
  ttsSubmitButton.disabled = true;

  try {
    const { response, data } = await fetchJson(
      "/voice/speak",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      },
      45000
    );

    if (!response.ok || data.status !== "ok" || !data.audio_url) {
      throw new Error(data.error || "tts failed");
    }

    ttsStatusText.textContent = "สร้างเสียงแล้ว";
    await loadAudioWithRetry(ttsAudioPlayer, data.audio_url, true);
    await refreshDashboardStatus();
    await refreshVoiceDebugStatus();
  } catch (error) {
    ttsStatusText.textContent = getReadableErrorMessage(error, "สร้างเสียงไม่สำเร็จ");
    await refreshVoiceDebugStatus();
  } finally {
    ttsSubmitButton.disabled = false;
  }
});

weatherForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const location = weatherLocation.value.trim();
  const message = location ? `วันนี้${location}อากาศยังไง` : "วันนี้อากาศยังไง";
  weatherResult.textContent = "กำลังถามข้อมูลอากาศ...";
  weatherResult.classList.remove("muted");
  await sendChatMessage(message);
});

window.addEventListener("online", () => {
  if (!state.chatBusy && !state.recording) {
    setPillState(chatStatus, "neutral", "พร้อมใช้งาน");
  }
});

window.addEventListener("offline", () => {
  setPillState(chatStatus, "bad", "ออฟไลน์");
});

window.addEventListener("beforeunload", () => {
  clearAutoListenTimer();
  if (state.speechRecognition) {
    state.speechRecognition.abort();
    state.speechRecognition = null;
  }
  cleanupMediaStream();
  for (const audioElement of document.querySelectorAll("audio")) {
    revokeAudioObjectUrl(audioElement);
  }
});

appendMessage(
  "assistant",
  "พร้อมทดสอบแล้ว ลองกดปุ่มตัวอย่าง พิมพ์ข้อความภาษาไทย หรือกดปุ่มไมค์เพื่อคุยด้วยเสียงได้เลย",
  { source: "placeholder" }
);

if (browserSupportsSpeechRecognition()) {
  setMicStatus("ไมโครโฟนพร้อมใช้งาน โหมดฟังเสียงในเบราว์เซอร์จะถูกใช้ก่อน");
} else if (browserSupportsRecording()) {
  setMicStatus("ไมโครโฟนพร้อมใช้งานเมื่ออนุญาตจากเบราว์เซอร์");
} else {
  setMicStatus("เบราว์เซอร์นี้ยังไม่รองรับการอัดเสียงสำหรับเดโมนี้", "busy");
  chatMicButton.disabled = true;
}

setMicState("closed");
setKeepMicIndicator(false, "พร้อมเริ่มคุยต่อเนื่องเมื่อกดไมค์");
setPillState(chatStatus, "neutral", "พร้อมใช้งาน");
setChatBusy(false);
refreshDashboardStatus();
refreshVoiceDebugStatus();
window.setInterval(refreshDashboardStatus, 15000);
window.setInterval(refreshVoiceDebugStatus, 5000);
