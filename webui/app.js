const chatHistory = document.getElementById("chat-history");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatLoading = document.getElementById("chat-loading");
const chatStatus = document.getElementById("chat-status");
const chatSendButton = document.getElementById("chat-send-button");
const quickActions = document.getElementById("quick-actions");

const sensorTemperature = document.getElementById("sensor-temperature");
const sensorHumidity = document.getElementById("sensor-humidity");
const sensorFreshness = document.getElementById("sensor-freshness");
const sensorUpdated = document.getElementById("sensor-updated");
const sensorDeviceId = document.getElementById("sensor-device-id");

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
const relayOnButton = document.getElementById("relay-on-button");
const relayOffButton = document.getElementById("relay-off-button");

const state = {
  chatBusy: false,
  maxChatHistoryItems: 50,
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

function setPillState(element, tone, text) {
  element.className = `status-pill ${tone}`;
  element.textContent = text;
}

function getChatActionButtons() {
  return [
    chatSendButton,
    weatherSubmitButton,
    relayOnButton,
    relayOffButton,
    ...quickActions.querySelectorAll("button[data-message]"),
  ];
}

function setChatBusy(isBusy) {
  state.chatBusy = isBusy;
  chatInput.disabled = isBusy;
  for (const button of getChatActionButtons()) {
    button.disabled = isBusy;
  }
  chatLoading.hidden = !isBusy;

  if (isBusy) {
    setPillState(chatStatus, "warn", "กำลังประมวลผล");
  } else if (!navigator.onLine) {
    setPillState(chatStatus, "bad", "ออฟไลน์");
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

function appendMessage(role, text, meta = {}) {
  const wrapper = document.createElement("article");
  wrapper.className = `message ${role}`;

  const timestamp = new Date().toLocaleTimeString("th-TH", {
    hour: "2-digit",
    minute: "2-digit",
  });

  const header = document.createElement("div");
  header.className = "message-header";

  const roleLabel = document.createElement("span");
  roleLabel.className = "message-role";
  roleLabel.textContent = role === "user" ? "คุณ" : "AI";

  const timeLabel = document.createElement("span");
  timeLabel.className = "message-time";
  timeLabel.textContent = timestamp;

  header.append(roleLabel, timeLabel);

  const body = document.createElement("p");
  body.className = "message-text";
  body.textContent = text;

  wrapper.append(header, body);

  if (meta.intent || meta.source) {
    const metaRow = document.createElement("div");
    metaRow.className = "message-meta";

    if (meta.intent) {
      const intentBadge = document.createElement("span");
      intentBadge.className = "badge";
      intentBadge.textContent = `intent: ${meta.intent}`;
      metaRow.appendChild(intentBadge);
    }

    if (meta.source) {
      const sourceBadge = document.createElement("span");
      sourceBadge.className = "badge";
      sourceBadge.textContent = `source: ${meta.source}`;
      metaRow.appendChild(sourceBadge);
    }

    wrapper.appendChild(metaRow);
  }

  if (meta.audioUrl) {
    const audio = document.createElement("audio");
    audio.controls = true;
    audio.preload = "metadata";

    const audioStatus = document.createElement("p");
    audioStatus.className = "audio-status";
    audioStatus.textContent = "กำลังเตรียมเสียง...";

    wrapper.append(audio, audioStatus);
    loadAudioWithRetry(audio, meta.audioUrl, true, audioStatus, 0, text);
  }

  chatHistory.appendChild(wrapper);
  trimChatHistory();
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

function attachAudioBlob(audioElement, blobUrl) {
  revokeAudioObjectUrl(audioElement);
  audioElement.dataset.objectUrl = blobUrl;
  audioElement.src = blobUrl;
  audioElement.load();
}

async function loadAudioWithRetry(
  audioElement,
  url,
  autoplay = false,
  statusElement = null,
  attempt = 0,
  recoveryText = null,
  hasRecovered = false
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
    if (attempt < maxAttempts - 1) {
      window.setTimeout(() => {
        loadAudioWithRetry(
          audioElement,
          url,
          autoplay,
          statusElement,
          attempt + 1,
          recoveryText,
          hasRecovered
        );
      }, 750);
      return;
    }

    if (recoveryText && !hasRecovered) {
      if (statusElement) {
        statusElement.textContent = "กำลังลองสร้างเสียงใหม่อีกครั้ง...";
      }

      try {
        const regeneratedAudioUrl = await requestSpeechAudioUrl(recoveryText);
        await loadAudioWithRetry(
          audioElement,
          regeneratedAudioUrl,
          autoplay,
          statusElement,
          0,
          null,
          true
        );
        return;
      } catch (recoveryError) {
        // Let the UI fall through to the final error state below.
      }
    }

    if (statusElement) {
      statusElement.textContent = "ยังสร้างเสียงไม่สำเร็จ ลองใหม่อีกครั้งได้";
    }
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

  if (data.current_token !== token || !data.audio_ready) {
    throw new Error("audio not ready");
  }
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

async function ensureChatAudioUrl(replyText, audioUrl) {
  if (audioUrl) {
    return audioUrl;
  }
  if (!replyText || !replyText.trim()) {
    return null;
  }

  return requestSpeechAudioUrl(replyText.trim());
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

async function sendChatMessage(message) {
  const trimmed = message.trim();
  if (!trimmed || state.chatBusy) {
    return;
  }

  appendMessage("user", trimmed);
  chatInput.value = "";
  setChatBusy(true);

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

    let resolvedAudioUrl = null;
    try {
      resolvedAudioUrl = await ensureChatAudioUrl(data.reply, data.audio_url || null);
    } catch (audioError) {
      resolvedAudioUrl = null;
    }

    appendMessage("assistant", data.reply, {
      intent: data.intent,
      source: data.source,
      audioUrl: resolvedAudioUrl,
    });
    setPillState(chatStatus, "good", "ตอบแล้ว");

    if (data.intent === "weather_query") {
      weatherResult.textContent = data.reply;
      weatherResult.classList.remove("muted");
    }

    await refreshDashboardStatus();
    await refreshVoiceDebugStatus();
  } catch (error) {
    const messageText = getReadableErrorMessage(
      error,
      "เกิดปัญหาระหว่างส่งข้อความ ลองใหม่อีกครั้งได้ไหม"
    );
    appendMessage("assistant", messageText, { source: "fallback" });
    setPillState(chatStatus, "bad", "เกิดข้อผิดพลาด");
  } finally {
    setChatBusy(false);
  }
}

async function refreshDashboardStatus() {
  try {
    const { response, data } = await fetchJson("/dashboard/status", {}, 10000);
    if (!response.ok) {
      throw new Error("dashboard status failed");
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
    sensorFreshness.textContent = data.sensor.is_fresh
      ? "ข้อมูลล่าสุดพร้อมใช้งาน"
      : "ยังไม่มีข้อมูลใหม่";
    sensorUpdated.textContent = formatDate(data.sensor.received_at || data.sensor.timestamp);

    setPillState(
      deviceOnlineIndicator,
      data.device.online ? "good" : "warn",
      data.device.online ? "ESP32 online" : "ESP32 offline"
    );
    deviceLatestCommand.textContent = data.device.latest_command
      ? `relay ch${data.device.latest_command.channel} -> ${data.device.latest_command.action}`
      : "-";
    devicePendingCount.textContent = String(data.device.pending_command_count ?? 0);
    deviceLastSeen.textContent = formatDate(data.device.last_seen_at);

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
    setPillState(deviceOnlineIndicator, "bad", "อ่านสถานะไม่ได้");
    setPillState(voiceModeIndicator, "bad", "อ่านสถานะไม่ได้");
  }
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await sendChatMessage(chatInput.value);
});

quickActions.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-message]");
  if (!button || button.disabled) {
    return;
  }
  await sendChatMessage(button.dataset.message || "");
});

sensorRefreshButton.addEventListener("click", refreshDashboardStatus);
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
    ttsStatusText.textContent = getReadableErrorMessage(
      error,
      "สร้างเสียงไม่สำเร็จ"
    );
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
  if (!state.chatBusy) {
    setPillState(chatStatus, "neutral", "พร้อมใช้งาน");
  }
});

window.addEventListener("offline", () => {
  setPillState(chatStatus, "bad", "ออฟไลน์");
});

window.addEventListener("beforeunload", () => {
  for (const audioElement of document.querySelectorAll("audio")) {
    revokeAudioObjectUrl(audioElement);
  }
});

appendMessage(
  "assistant",
  "พร้อมทดสอบแล้ว ลองกดปุ่มตัวอย่างหรือพิมพ์ข้อความภาษาไทยได้เลย",
  { source: "placeholder" }
);

setPillState(chatStatus, "neutral", "พร้อมใช้งาน");
setChatBusy(false);
refreshDashboardStatus();
refreshVoiceDebugStatus();
window.setInterval(refreshDashboardStatus, 15000);
window.setInterval(refreshVoiceDebugStatus, 5000);
