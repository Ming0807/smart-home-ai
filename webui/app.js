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
const voiceModePushButton = document.getElementById("voice-mode-push");
const voiceModeWakeButton = document.getElementById("voice-mode-wake");
const chatModeFastButton = document.getElementById("chat-mode-fast");
const chatModeThinkingButton = document.getElementById("chat-mode-thinking");
const chatResponseModeLabel = document.getElementById("chat-response-mode-label");
const thinkingTestActions = document.getElementById("thinking-test-actions");

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

const llmStatusIndicator = document.getElementById("llm-status-indicator");
const llmWarmupButton = document.getElementById("llm-warmup-button");
const llmSleepButton = document.getElementById("llm-sleep-button");
const llmWarmupStatus = document.getElementById("llm-warmup-status");
const llmModel = document.getElementById("llm-model");
const llmWarmed = document.getElementById("llm-warmed");
const llmKeepAwake = document.getElementById("llm-keep-awake");
const llmLatency = document.getElementById("llm-latency");
const llmChecked = document.getElementById("llm-checked");
const llmError = document.getElementById("llm-error");

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

const WAKE_PHRASE_PATTERNS = [
  /น้อง\s*ฟ้า/iu,
  /น้อง\s*ฟ่า/iu,
  /น้อง\s*ฟา/iu,
  /นอง\s*ฟ้า/iu,
  /nong\s*fa/i,
];

const EXIT_WORDS = ["ขอบคุณ", "พอแล้ว", "เลิกคุย", "แค่นี้แหละ"];
const VOICE_STATE_STOPPED = "STOPPED";
const VOICE_STATE_IDLE_WAKE = "IDLE_LISTENING_WAKE_WORD";
const VOICE_STATE_ACTIVE = "ACTIVE_CONVERSATION";
const ACTIVE_LISTEN_RETRY_LIMIT = 2;
const ACTIVE_LISTEN_RETRY_DELAY_MS = 900;
const POST_SPEAKING_COOLDOWN_MS = 1800;
const WAKE_LISTEN_RESTART_DELAY_MS = 350;
const WAKE_LISTEN_WATCHDOG_MS = 15000;
const VOICE_RECORD_MIN_MS = 900;
const VOICE_RECORD_MAX_MS = 12000;
const VOICE_NO_SPEECH_TIMEOUT_MS = 6500;
const VOICE_SILENCE_STOP_MS = 1200;
const VOICE_SPEECH_RMS_THRESHOLD = 0.012;
const SPEECH_RECOGNITION_TURN_TIMEOUT_MS = 12000;
const SPEECH_RECOGNITION_LOOP_RESTART_MS = 500;
const ASSISTANT_ECHO_WINDOW_MS = 6000;
const DUPLICATE_TRANSCRIPT_WINDOW_MS = 2000;
const CHAT_REQUEST_TIMEOUT_MS = 70000;
const CHAT_WAITING_HINT_DELAY_MS = 6000;
const CHAT_LONG_WAIT_HINT_DELAY_MS = 18000;
const CHAT_MODE_FAST = "fast";
const CHAT_MODE_THINKING = "thinking";
const THINKING_TRIGGER_PREFIX = "คิดก่อนตอบ";
const THINKING_TRIGGER_PHRASES = [
  "คิดก่อนตอบ",
  "คิดก่อน",
  "วิเคราะห์ก่อน",
  "ขอคิดละเอียด",
  "คิดให้ละเอียด",
  "ขอวิเคราะห์",
  "deep think",
  "think carefully",
];
const REAL_THINKING_TRIGGER_PHRASES = [
  "คิดลึกจริง",
  "คิดแบบลึกจริง",
  "ใช้ thinking จริง",
  "เปิด thinking จริง",
  "real thinking",
  "deep think true",
];

const state = {
  chatBusy: false,
  recording: false,
  speechRecognition: null,
  recognitionMode: null,
  mediaRecorder: null,
  mediaStream: null,
  audioChunks: [],
  audioContext: null,
  audioAnalyser: null,
  voiceRecordAnimationId: null,
  voiceRecordTimeoutId: null,
  speechRecognitionTimeoutId: null,
  voiceLoopRestartTimerId: null,
  discardCurrentRecording: false,
  maxChatHistoryItems: 50,
  chatResponseMode: CHAT_MODE_FAST,
  keepMicOpen: false,
  voiceRequestActive: false,
  stopRequested: false,
  autoListenTimerId: null,
  wakeListenWatchdogId: null,
  pirTouched: false,
  voiceMode: "push",
  wakeListening: false,
  conversationActive: false,
  voiceState: VOICE_STATE_STOPPED,
  activeListenRetryCount: 0,
  lastAssistantReplyText: "",
  lastAssistantPlaybackEndedAt: 0,
  lastHandledTranscript: "",
  lastHandledTranscriptAt: 0,
  chatWaitTimerIds: [],
};

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

function setVoiceSessionState(mode) {
  if (mode === VOICE_STATE_STOPPED) {
    setPillState(micStateIndicator, "neutral", "ปิดไมค์แล้ว");
    return;
  }
  if (mode === VOICE_STATE_IDLE_WAKE || mode === "wake") {
    setPillState(micStateIndicator, "neutral", "กำลังรอคำว่า น้องฟ้า");
    return;
  }
  if (mode === VOICE_STATE_ACTIVE || mode === "active") {
    setPillState(micStateIndicator, "good", "กำลังสนทนา");
    return;
  }
  if (mode === "processing") {
    setPillState(micStateIndicator, "warn", "กำลังประมวลผล");
    return;
  }
  if (mode === "speaking") {
    setPillState(micStateIndicator, "good", "กำลังพูด");
    return;
  }
  setPillState(micStateIndicator, "neutral", "พร้อมเริ่มคุย");
}

function setVoiceLifecycleState(nextState) {
  state.voiceState = nextState;
  setVoiceSessionState(nextState);
}

function setKeepMicIndicator(keepOpen, reason = "") {
  state.keepMicOpen = keepOpen;
  if (keepOpen) {
    setPillState(keepMicIndicator, "good", "keep_mic_open: true");
    voiceTurnStatus.textContent = reason || "AI ขอเปิดไมค์ต่อ";
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

function clearWakeListenWatchdog() {
  if (state.wakeListenWatchdogId !== null) {
    window.clearTimeout(state.wakeListenWatchdogId);
    state.wakeListenWatchdogId = null;
  }
}

function scheduleWakeListenWatchdog() {
  clearWakeListenWatchdog();
  if (state.voiceMode !== "wake" || state.stopRequested) {
    return;
  }
  state.wakeListenWatchdogId = window.setTimeout(() => {
    state.wakeListenWatchdogId = null;
    if (state.speechRecognition && state.recognitionMode === "loop") {
      pauseSpeechRecognitionLoop();
      restartSpeechRecognitionLoop(300);
    }
  }, WAKE_LISTEN_WATCHDOG_MS);
}

function clearSpeechRecognitionTimeout() {
  if (state.speechRecognitionTimeoutId !== null) {
    window.clearTimeout(state.speechRecognitionTimeoutId);
    state.speechRecognitionTimeoutId = null;
  }
}

function clearVoiceLoopRestartTimer() {
  if (state.voiceLoopRestartTimerId !== null) {
    window.clearTimeout(state.voiceLoopRestartTimerId);
    state.voiceLoopRestartTimerId = null;
  }
}

function clearChatWaitHints() {
  for (const timerId of state.chatWaitTimerIds) {
    window.clearTimeout(timerId);
  }
  state.chatWaitTimerIds = [];
}

function setChatLoadingText(text) {
  chatLoading.textContent = text;
}

function startChatWaitHints(isThinkingMode = false) {
  clearChatWaitHints();
  setChatLoadingText(isThinkingMode ? "AI กำลังคิดก่อนตอบ..." : "AI กำลังตอบ...");
  state.chatWaitTimerIds = [
    window.setTimeout(() => {
      setChatLoadingText(
        isThinkingMode
          ? "โหมดคิดก่อนตอบเร็วกำลังวิเคราะห์ รอสักครู่นะ..."
          : "กำลังคิดคำตอบจากโมเดลหลัก รอสักครู่นะ..."
      );
      setPillState(chatStatus, "warn", isThinkingMode ? "วิเคราะห์เร็ว" : "กำลังคิด");
    }, CHAT_WAITING_HINT_DELAY_MS),
    window.setTimeout(() => {
      setChatLoadingText(
        isThinkingMode
          ? "ยังวิเคราะห์อยู่ ระบบจะสร้างเสียงหลังคำตอบจริงมาถึงเท่านั้น"
          : "ยังคิดอยู่ ข้อความรอนี้จะไม่สร้างเสียงจนกว่าคำตอบจริงจะมา"
      );
      setPillState(chatStatus, "warn", "LLM กำลังทำงาน");
    }, CHAT_LONG_WAIT_HINT_DELAY_MS),
  ];
}

function resetActiveListenRetries() {
  state.activeListenRetryCount = 0;
}

function rememberHandledTranscript(transcript) {
  state.lastHandledTranscript = normalizeThaiText(transcript);
  state.lastHandledTranscriptAt = Date.now();
}

function isDuplicateTranscript(transcript) {
  const normalized = normalizeThaiText(transcript);
  if (!normalized) {
    return false;
  }
  if (normalized !== state.lastHandledTranscript) {
    return false;
  }
  return Date.now() - state.lastHandledTranscriptAt <= DUPLICATE_TRANSCRIPT_WINDOW_MS;
}

function scheduleWakeWordResume(delayMs = WAKE_LISTEN_RESTART_DELAY_MS) {
  if (state.voiceMode !== "wake" || state.stopRequested) {
    return;
  }

  clearWakeListenWatchdog();
  clearVoiceLoopRestartTimer();
  state.conversationActive = false;
  state.wakeListening = false;
  state.recording = false;
  setVoiceLifecycleState(VOICE_STATE_IDLE_WAKE);
  setKeepMicIndicator(false, "กำลังรอฟังคำว่า น้องฟ้า");
  chatMicButton.textContent = "Start talking";
  setChatBusy(false);
  clearAutoListenTimer();
  state.autoListenTimerId = window.setTimeout(() => {
    state.autoListenTimerId = null;
    startSpeechRecognitionLoop();
  }, delayMs);
}

function keepWakeWordModeAlive(reason = "กลับไปรอฟังคำว่า น้องฟ้า", delayMs = WAKE_LISTEN_RESTART_DELAY_MS) {
  if (state.voiceMode !== "wake" || state.stopRequested) {
    return false;
  }

  state.conversationActive = false;
  setKeepMicIndicator(false, reason);
  scheduleWakeWordResume(delayMs);
  return true;
}

function scheduleActiveConversationRetry(reason, delayMs = ACTIVE_LISTEN_RETRY_DELAY_MS) {
  if (
    state.stopRequested ||
    !state.conversationActive ||
    state.chatBusy ||
    state.recording ||
    state.activeListenRetryCount >= ACTIVE_LISTEN_RETRY_LIMIT
  ) {
    state.conversationActive = false;
    resetActiveListenRetries();
    if (state.voiceMode === "wake") {
      scheduleWakeWordResume();
    } else {
      setVoiceLifecycleState(VOICE_STATE_STOPPED);
    }
    return false;
  }

  state.activeListenRetryCount += 1;
  setVoiceLifecycleState(VOICE_STATE_ACTIVE);
  setKeepMicIndicator(true, reason);
  setMicStatus(reason, "live");
  clearAutoListenTimer();
  state.autoListenTimerId = window.setTimeout(() => {
    state.autoListenTimerId = null;
    startActiveConversationTurn();
  }, delayMs);
  return true;
}

function browserSupportsRecording() {
  return Boolean(window.MediaRecorder && navigator.mediaDevices?.getUserMedia);
}

function browserSupportsSpeechRecognition() {
  return Boolean(SpeechRecognitionConstructor);
}

function updateVoiceModeButtons() {
  voiceModePushButton.classList.toggle("active", state.voiceMode === "push");
  voiceModeWakeButton.classList.toggle("active", state.voiceMode === "wake");
  chatMicButton.textContent = "Start talking";
}

function normalizeModeTriggerText(text) {
  return text.toLocaleLowerCase().replace(/\s+/g, "");
}

function messageHasThinkingTrigger(message) {
  const normalizedMessage = normalizeModeTriggerText(message);
  const triggerPhrases = [...THINKING_TRIGGER_PHRASES, ...REAL_THINKING_TRIGGER_PHRASES];
  return triggerPhrases.some((phrase) =>
    normalizedMessage.includes(normalizeModeTriggerText(phrase))
  );
}

function shouldUseThinkingModeForMessage(message) {
  return state.chatResponseMode === CHAT_MODE_THINKING || messageHasThinkingTrigger(message);
}

function buildChatApiMessage(message) {
  if (state.chatResponseMode !== CHAT_MODE_THINKING || messageHasThinkingTrigger(message)) {
    return message;
  }
  return `${THINKING_TRIGGER_PREFIX} ${message}`;
}

function updateChatResponseModeButtons() {
  chatModeFastButton.classList.toggle("active", state.chatResponseMode === CHAT_MODE_FAST);
  chatModeThinkingButton.classList.toggle(
    "active",
    state.chatResponseMode === CHAT_MODE_THINKING
  );

  if (state.chatResponseMode === CHAT_MODE_THINKING) {
    setPillState(chatResponseModeLabel, "warn", "โหมดคิดก่อนตอบเร็ว");
    return;
  }
  setPillState(chatResponseModeLabel, "neutral", "โหมดตอบเร็ว");
}

function setChatResponseMode(mode) {
  if (state.chatBusy || state.recording) {
    return;
  }
  state.chatResponseMode = mode === CHAT_MODE_THINKING ? CHAT_MODE_THINKING : CHAT_MODE_FAST;
  updateChatResponseModeButtons();
}

function isMediaRecorderActive() {
  return Boolean(state.mediaRecorder && state.mediaRecorder.state !== "inactive");
}

function hasActiveVoiceCapture() {
  return Boolean(state.speechRecognition || isMediaRecorderActive());
}

function clearSpeechRecognitionIfCurrent(recognition) {
  if (state.speechRecognition !== recognition) {
    return;
  }
  state.speechRecognition = null;
  state.recognitionMode = null;
}

function syncVoiceCaptureState() {
  if (state.speechRecognition) {
    state.recording = state.recognitionMode === "turn";
    state.wakeListening = state.recognitionMode === "wake" || state.recognitionMode === "loop";
    return;
  }

  if (isMediaRecorderActive()) {
    state.recording = true;
    state.wakeListening = false;
    return;
  }

  state.recording = false;
  state.wakeListening = false;
  state.recognitionMode = null;
}

function getChatActionButtons() {
  return [
    chatSendButton,
    chatMicButton,
    chatStopButton,
    weatherSubmitButton,
    relayOnButton,
    relayOffButton,
    voiceModePushButton,
    voiceModeWakeButton,
    chatModeFastButton,
    chatModeThinkingButton,
    ...quickActions.querySelectorAll("button[data-message]"),
    ...thinkingTestActions.querySelectorAll("button[data-test-message]"),
    ...exitQuickActions.querySelectorAll("button[data-exit-message]"),
  ];
}

function setChatBusy(isBusy) {
  syncVoiceCaptureState();
  state.chatBusy = isBusy;
  const captureActive = hasActiveVoiceCapture();
  const controlsDisabled = isBusy || state.recording;
  const canStopVoice =
    captureActive ||
    state.wakeListening ||
    state.conversationActive ||
    (state.voiceMode === "wake" && state.voiceState !== VOICE_STATE_STOPPED && !state.stopRequested);

  chatInput.disabled = controlsDisabled;
  pirSimToggle.disabled = isBusy;

  for (const button of getChatActionButtons()) {
    if ((button === chatMicButton || button === chatStopButton) && canStopVoice) {
      button.disabled = false;
      continue;
    }
    if (button === chatStopButton) {
      button.disabled = !canStopVoice;
      continue;
    }
    button.disabled = controlsDisabled;
  }

  chatLoading.hidden = !isBusy;

  if (isBusy) {
    if (state.voiceRequestActive) {
      chatMicButton.textContent = "กำลังตอบ...";
    }
    setPillState(chatStatus, "warn", "กำลังประมวลผล");
  } else if (state.recording || state.wakeListening || state.voiceState === VOICE_STATE_IDLE_WAKE) {
    chatMicButton.textContent = state.recording && captureActive ? "Stop" : "Start talking";
    setPillState(chatStatus, "warn", "กำลังฟังเสียง");
  } else if (!navigator.onLine) {
    chatMicButton.textContent = "Start talking";
    setPillState(chatStatus, "bad", "ออฟไลน์");
  } else {
    chatMicButton.textContent = "Start talking";
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

async function fetchChatStream(message, handlers = {}) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), CHAT_REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch("/chat/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({ message }),
      cache: "no-store",
      signal: controller.signal,
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || "stream request failed");
    }
    if (!response.body) {
      throw new Error("streaming is not supported by this browser");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalData = null;

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split(/\r?\n\r?\n/);
      buffer = blocks.pop() || "";

      for (const block of blocks) {
        if (!block.trim()) {
          continue;
        }
        const parsed = parseSseBlock(block);
        if (parsed.event === "chunk") {
          handlers.onChunk?.(parsed.data.text || "");
        } else if (parsed.event === "status") {
          handlers.onStatus?.(parsed.data.message || "");
        } else if (parsed.event === "done") {
          finalData = parsed.data;
          handlers.onDone?.(parsed.data);
        }
      }
    }

    if (buffer.trim()) {
      const parsed = parseSseBlock(buffer);
      if (parsed.event === "done") {
        finalData = parsed.data;
      }
    }

    if (!finalData) {
      throw new Error("stream ended without final response");
    }
    return finalData;
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
      return loadAudioWithRetry(audioElement, url, autoplay, statusElement, attempt + 1, recoveryText);
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

function appendMessageMeta(wrapper, meta = {}) {
  const existingMeta = wrapper.querySelector(".message-meta");
  if (existingMeta) {
    existingMeta.remove();
  }

  if (
    !meta.intent &&
    !meta.source &&
    !meta.action &&
    !meta.mode &&
    typeof meta.latencyMs !== "number" &&
    typeof meta.keepMicOpen !== "boolean"
  ) {
    return;
  }

  const metaRow = document.createElement("div");
  metaRow.className = "message-meta";

  for (const [key, value] of [
    ["intent", meta.intent],
    ["source", meta.source],
    ["action", meta.action],
    ["mode", meta.mode],
  ]) {
    if (!value) {
      continue;
    }
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = `${key}: ${value}`;
    metaRow.appendChild(badge);
  }

  const formattedLatency = formatChatLatencyMs(meta.latencyMs);
  if (formattedLatency) {
    const latencyBadge = document.createElement("span");
    latencyBadge.className = "badge";
    latencyBadge.textContent = `latency: ${formattedLatency}`;
    metaRow.appendChild(latencyBadge);
  }

  if (typeof meta.keepMicOpen === "boolean") {
    const keepBadge = document.createElement("span");
    keepBadge.className = "badge";
    keepBadge.textContent = `keep_mic_open: ${meta.keepMicOpen ? "true" : "false"}`;
    metaRow.appendChild(keepBadge);
  }

  wrapper.appendChild(metaRow);
}

function attachMessageAudio(wrapper, text, audioUrl) {
  for (const audioElement of wrapper.querySelectorAll("audio")) {
    revokeAudioObjectUrl(audioElement);
    audioElement.remove();
  }
  for (const audioStatus of wrapper.querySelectorAll(".audio-status")) {
    audioStatus.remove();
  }

  if (!audioUrl) {
    return {
      audioElement: null,
      audioPromise: Promise.resolve(),
    };
  }

  const audioElement = document.createElement("audio");
  audioElement.controls = true;
  audioElement.preload = "metadata";

  const audioStatus = document.createElement("p");
  audioStatus.className = "audio-status";
  audioStatus.textContent = "กำลังเตรียมเสียง...";

  wrapper.append(audioElement, audioStatus);
  const audioPromise = loadAudioWithRetry(audioElement, audioUrl, true, audioStatus, 0, text);
  return { audioElement, audioPromise };
}

function scrollChatToBottom() {
  chatHistory.scrollTop = chatHistory.scrollHeight;
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
  appendMessageMeta(wrapper, meta);

  const { audioElement, audioPromise } = attachMessageAudio(wrapper, text, meta.audioUrl || null);

  chatHistory.appendChild(wrapper);
  trimChatHistory();
  scrollChatToBottom();
  return { wrapper, body, audioElement, audioPromise };
}

function appendStreamingAssistantMessage() {
  const entry = appendMessage("assistant", "กำลังเริ่มตอบจากโมเดลหลัก...", {
    source: "ollama",
  });
  entry.wrapper.classList.add("streaming");
  return entry;
}

function updateAssistantEntryText(entry, text) {
  entry.body.textContent = text || "กำลังคิดคำตอบจากโมเดลหลัก...";
  scrollChatToBottom();
}

async function finalizeAssistantEntry(entry, data, options = {}) {
  entry.wrapper.classList.remove("streaming");
  entry.body.textContent = data.reply || "";
  state.lastAssistantReplyText = data.reply || "";
  appendMessageMeta(entry.wrapper, {
    intent: data.intent,
    source: data.source,
    action: data.action,
    keepMicOpen: data.keep_mic_open,
    latencyMs: options.latencyMs,
  });

  let resolvedAudioUrl = null;
  try {
    resolvedAudioUrl = await ensureChatAudioUrl(data.reply, data.audio_url || null);
  } catch (audioError) {
    resolvedAudioUrl = null;
  }

  const audioState = attachMessageAudio(entry.wrapper, data.reply || "", resolvedAudioUrl);
  entry.audioElement = audioState.audioElement;
  entry.audioPromise = audioState.audioPromise;
  scrollChatToBottom();
  return entry;
}

function normalizeVoicePayload(payload) {
  if (payload && payload.data) {
    return payload.data;
  }
  return payload;
}

function isExitPhrase(text) {
  const normalized = normalizeThaiText(text);
  return EXIT_WORDS.some((word) => normalized.includes(normalizeThaiText(word)));
}

function detectWakePhrase(text) {
  for (const pattern of WAKE_PHRASE_PATTERNS) {
    const match = text.match(pattern);
    if (!match) {
      continue;
    }
    const remaining = text
      .replace(pattern, "")
      .replace(/^[\s,.!?-]+|[\s,.!?-]+$/g, "")
      .trim();
    return {
      matched: match[0],
      remaining,
    };
  }
  return null;
}

function createSpeechRecognition(mode) {
  if (!SpeechRecognitionConstructor) {
    return null;
  }

  const recognition = new SpeechRecognitionConstructor();
  recognition.lang = "th-TH";
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  state.recognitionMode = mode;
  return recognition;
}

function collectSpeechResultText(event) {
  const finalParts = [];
  const interimParts = [];

  for (let index = event.resultIndex || 0; index < event.results.length; index += 1) {
    const result = event.results[index];
    const text = result[0]?.transcript || "";
    if (!text) {
      continue;
    }
    if (result.isFinal) {
      finalParts.push(text);
    } else {
      interimParts.push(text);
    }
  }

  return {
    finalText: finalParts.join(" ").trim(),
    interimText: interimParts.join(" ").trim(),
  };
}

function shouldKeepSpeechLoopRunning() {
  return (
    state.voiceMode === "wake" &&
    !state.stopRequested &&
    !state.chatBusy &&
    !state.voiceRequestActive
  );
}

function detachSpeechRecognition(recognition) {
  recognition.onresult = null;
  recognition.onerror = null;
  recognition.onend = null;
  recognition.onnomatch = null;
  recognition.onspeechend = null;
}

function pauseSpeechRecognitionLoop() {
  clearSpeechRecognitionTimeout();
  clearVoiceLoopRestartTimer();

  const recognition = state.speechRecognition;
  if (recognition) {
    detachSpeechRecognition(recognition);
    try {
      recognition.abort();
    } catch (error) {
      // Chrome may already have closed this recognition cycle.
    }
  }

  state.speechRecognition = null;
  state.recognitionMode = null;
  state.recording = false;
  state.wakeListening = false;
  chatMicButton.textContent = "Start talking";
}

function restartSpeechRecognitionLoop(delayMs = SPEECH_RECOGNITION_LOOP_RESTART_MS) {
  if (!shouldKeepSpeechLoopRunning()) {
    return false;
  }

  clearVoiceLoopRestartTimer();
  state.voiceLoopRestartTimerId = window.setTimeout(() => {
    state.voiceLoopRestartTimerId = null;
    startSpeechRecognitionLoop();
  }, delayMs);
  return true;
}

async function handleSpeechLoopTranscript(transcript) {
  const text = transcript.trim();
  if (!text || state.chatBusy || state.voiceRequestActive) {
    return;
  }

  if (isDuplicateTranscript(text)) {
    setMicStatus("ได้ยินข้อความเดิมซ้ำ กำลังรอฟังต่อ...", "live");
    return;
  }

  if (isLikelyAssistantEcho(text)) {
    setMicStatus("ตัดเสียงสะท้อนของ AI แล้ว รอฟังต่อ...", "live");
    return;
  }

  if (!state.conversationActive) {
    const wakeMatch = detectWakePhrase(text);
    if (!wakeMatch) {
      setVoiceLifecycleState(VOICE_STATE_IDLE_WAKE);
      setMicStatus("กำลังรอคำว่า น้องฟ้า", "live");
      return;
    }

    state.conversationActive = true;
    setVoiceLifecycleState(VOICE_STATE_ACTIVE);
    setKeepMicIndicator(true, "ได้ยินคำเรียกแล้ว พูดต่อได้เลย");
    voiceTurnStatus.textContent = "ได้ยินคำว่า น้องฟ้า แล้ว";

    const remaining = wakeMatch.remaining.trim();
    if (!remaining) {
      showHeardText("น้องฟ้า");
      setMicStatus("กำลังฟังต่อ พูดคำถามได้เลย", "live");
      return;
    }

    rememberHandledTranscript(text);
    await sendVoiceText(remaining);
    return;
  }

  rememberHandledTranscript(text);
  await sendVoiceText(text);
}

function startSpeechRecognitionLoop() {
  if (state.voiceMode !== "wake" || state.stopRequested) {
    return false;
  }
  if (!browserSupportsSpeechRecognition()) {
    setMicStatus("Wake Word Mode ต้องใช้ Chrome หรือ Edge ที่รองรับ speech recognition", "busy");
    setVoiceLifecycleState(VOICE_STATE_STOPPED);
    return false;
  }
  if (state.chatBusy || state.voiceRequestActive) {
    return false;
  }
  if (state.speechRecognition && state.recognitionMode === "loop") {
    state.wakeListening = !state.conversationActive;
    if (state.conversationActive) {
      setVoiceLifecycleState(VOICE_STATE_ACTIVE);
      setMicStatus("กำลังฟังต่อ พูดได้เลย", "live");
    } else {
      setVoiceLifecycleState(VOICE_STATE_IDLE_WAKE);
      setMicStatus("กำลังรอคำว่า น้องฟ้า", "live");
    }
    setChatBusy(false);
    return true;
  }

  pauseSpeechRecognitionLoop();

  const recognition = createSpeechRecognition("loop");
  if (!recognition) {
    return false;
  }

  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  state.speechRecognition = recognition;
  state.recognitionMode = "loop";
  state.recording = false;
  state.wakeListening = !state.conversationActive;
  chatMicButton.textContent = "Start talking";

  if (state.conversationActive) {
    setVoiceLifecycleState(VOICE_STATE_ACTIVE);
    setMicStatus("กำลังฟังต่อ พูดได้เลย", "live");
  } else {
    setVoiceLifecycleState(VOICE_STATE_IDLE_WAKE);
    setMicStatus("กำลังรอคำว่า น้องฟ้า", "live");
  }
  setChatBusy(false);

  recognition.onresult = (event) => {
    if (state.speechRecognition !== recognition) {
      return;
    }

    const { finalText, interimText } = collectSpeechResultText(event);
    if (interimText) {
      showHeardText(interimText);
    }
    if (!finalText) {
      return;
    }

    showHeardText(finalText);
    void handleSpeechLoopTranscript(finalText);
  };

  recognition.onerror = (event) => {
    if (state.speechRecognition !== recognition) {
      return;
    }

    const errorName = event?.error || "";
    detachSpeechRecognition(recognition);
    clearSpeechRecognitionIfCurrent(recognition);
    state.recording = false;
    state.wakeListening = false;
    setChatBusy(false);

    if (errorName === "not-allowed" || errorName === "service-not-allowed") {
      state.stopRequested = true;
      state.conversationActive = false;
      setVoiceLifecycleState(VOICE_STATE_STOPPED);
      setMicStatus("เบราว์เซอร์ยังไม่อนุญาตไมค์ ต้องกดอนุญาตก่อน", "busy");
      return;
    }

    setMicStatus("ไมค์สะดุดนิดหน่อย กำลังเปิดฟังใหม่...", "live");
    restartSpeechRecognitionLoop(700);
  };

  recognition.onend = () => {
    if (state.speechRecognition !== recognition) {
      return;
    }

    detachSpeechRecognition(recognition);
    clearSpeechRecognitionIfCurrent(recognition);
    state.recording = false;
    state.wakeListening = false;
    if (shouldKeepSpeechLoopRunning()) {
      restartSpeechRecognitionLoop();
    }
  };

  try {
    recognition.start();
    scheduleWakeListenWatchdog();
    return true;
  } catch (error) {
    detachSpeechRecognition(recognition);
    clearSpeechRecognitionIfCurrent(recognition);
    state.recording = false;
    state.wakeListening = false;
    setChatBusy(false);
    setMicStatus("เปิดลูปฟังเสียงไม่สำเร็จ กำลังลองใหม่...", "busy");
    restartSpeechRecognitionLoop(900);
    return false;
  }
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

function clearVoiceRecordingMonitors() {
  if (state.voiceRecordAnimationId !== null) {
    window.cancelAnimationFrame(state.voiceRecordAnimationId);
    state.voiceRecordAnimationId = null;
  }
  if (state.voiceRecordTimeoutId !== null) {
    window.clearTimeout(state.voiceRecordTimeoutId);
    state.voiceRecordTimeoutId = null;
  }
  if (state.audioContext) {
    state.audioContext.close().catch(() => {});
  }
  state.audioContext = null;
  state.audioAnalyser = null;
}

function cleanupMediaStream() {
  clearVoiceRecordingMonitors();
  if (state.mediaStream) {
    for (const track of state.mediaStream.getTracks()) {
      track.stop();
    }
  }

  state.mediaStream = null;
  state.mediaRecorder = null;
  state.audioChunks = [];
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

function formatLatencyMs(latencyMs) {
  if (latencyMs === null || latencyMs === undefined || Number.isNaN(Number(latencyMs))) {
    return "-";
  }
  return `${Math.round(Number(latencyMs))} ms`;
}

function updateLlmStatus(llm) {
  if (!llm) {
    setPillState(llmStatusIndicator, "warn", "ยังไม่มีข้อมูล AI");
    llmModel.textContent = "-";
    llmWarmed.textContent = "-";
    llmKeepAwake.textContent = "-";
    llmLatency.textContent = "-";
    llmChecked.textContent = "-";
    llmError.textContent = "-";
    return;
  }

  if (llm.keep_awake_paused) {
    setPillState(llmStatusIndicator, "neutral", "AI พักอยู่");
  } else if (llm.available && llm.warmed_up) {
    setPillState(llmStatusIndicator, "good", "AI พร้อมคุย");
  } else if (llm.available) {
    setPillState(llmStatusIndicator, "warn", "AI ยังไม่ warm");
  } else {
    setPillState(llmStatusIndicator, "bad", "AI degraded");
  }

  llmModel.textContent = llm.model || "-";
  llmWarmed.textContent = llm.warmed_up ? "warm แล้ว" : "ยังไม่ warm";
  llmKeepAwake.textContent = llm.keep_awake_enabled
    ? llm.keep_awake_paused
      ? "พักไว้จนกดปลุก AI"
      : "เปิดอยู่"
    : "ปิดอยู่";
  llmLatency.textContent = formatLatencyMs(llm.latency_ms);
  llmChecked.textContent = formatDate(llm.checked_at);
  llmError.textContent = llm.last_error || (llm.available ? "พร้อมใช้งาน" : "ยังไม่พร้อม");
}

async function warmupLlm() {
  llmWarmupButton.disabled = true;
  llmWarmupStatus.textContent = "กำลังปลุก AI อาจใช้เวลานานเฉพาะรอบแรก...";
  setPillState(llmStatusIndicator, "warn", "กำลัง warm");

  try {
    const { response, data } = await fetchJson(
      "/health/llm/warmup",
      { method: "POST" },
      90000
    );
    if (!response.ok) {
      throw new Error("LLM warmup failed");
    }
    updateLlmStatus(data);
    llmWarmupStatus.textContent = data.available
      ? "ปลุก AI สำเร็จ พร้อมเดโม"
      : "ปลุก AI ไม่สำเร็จ ลองเช็ก Ollama และชื่อโมเดล";
  } catch (error) {
    llmWarmupStatus.textContent = getReadableErrorMessage(error, "ปลุก AI ไม่สำเร็จ");
    setPillState(llmStatusIndicator, "bad", "AI warmup failed");
  } finally {
    llmWarmupButton.disabled = false;
    await refreshDashboardStatus();
  }
}

async function sleepLlm() {
  llmSleepButton.disabled = true;
  llmWarmupStatus.textContent = "กำลังพัก AI ตามคำสั่ง...";
  setPillState(llmStatusIndicator, "neutral", "กำลังพัก");

  try {
    const { response, data } = await fetchJson(
      "/health/llm/sleep",
      { method: "POST" },
      30000
    );
    if (!response.ok) {
      throw new Error("LLM sleep failed");
    }
    updateLlmStatus(data);
    llmWarmupStatus.textContent = "พัก AI แล้ว ถ้าจะเดโมต่อให้กดปลุก AI";
  } catch (error) {
    llmWarmupStatus.textContent = getReadableErrorMessage(error, "พัก AI ไม่สำเร็จ");
    setPillState(llmStatusIndicator, "bad", "พัก AI ไม่สำเร็จ");
  } finally {
    llmSleepButton.disabled = false;
    await refreshDashboardStatus();
  }
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

  setVoiceSessionState("speaking");

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
    const textLength = (state.lastAssistantReplyText || "").length;
    const estimatedSpeechMs = Math.min(45000, Math.max(12000, textLength * 150));
    const durationMs = Number.isFinite(audioElement.duration)
      ? Math.round(audioElement.duration * 1000) + 1500
      : 0;
    const timeoutId = window.setTimeout(finish, Math.max(estimatedSpeechMs, durationMs));
    audioElement.addEventListener("ended", finish, { once: true });
    audioElement.addEventListener("error", finish, { once: true });
  });
  state.lastAssistantPlaybackEndedAt = Date.now();
}

function isLikelyAssistantEcho(transcript) {
  const normalizedTranscript = normalizeThaiText(transcript);
  const normalizedReply = normalizeThaiText(state.lastAssistantReplyText || "");
  if (!normalizedTranscript) {
    return false;
  }
  if (Date.now() - state.lastAssistantPlaybackEndedAt > ASSISTANT_ECHO_WINDOW_MS) {
    return false;
  }

  const assistantActionHints = [
    "ถ้าอยากฟังต่อ",
    "บอกได้เลยว่าเอาข้อไหน",
    "เอาข้อไหน",
    "ส่งข่าวเข้าline",
    "ส่งลิงก์ข่าว",
    "ส่งลิงค์ข่าว"
  ];
  if (assistantActionHints.some((hint) => normalizedTranscript.includes(normalizeThaiText(hint)))) {
    return true;
  }

  if (normalizedReply) {
    if (normalizedReply.includes(normalizedTranscript)) {
      return true;
    }
    if (normalizedTranscript.length >= 18) {
      const head = normalizedTranscript.slice(0, 18);
      const tail = normalizedTranscript.slice(-18);
      if (normalizedReply.includes(head) || normalizedReply.includes(tail)) {
        return true;
      }
    }
  }

  return false;
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
      // keep aggregate state
    }

    state.maxChatHistoryItems =
      Number.isFinite(data.app?.max_chat_history_items) && data.app.max_chat_history_items > 0
        ? data.app.max_chat_history_items
        : state.maxChatHistoryItems;
    trimChatHistory();
    updateLlmStatus(data.llm);

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
  const {
    appendUserMessage = true,
    userMessage = "",
    heardText = "",
    refreshStatus = true,
    latencyMs,
  } = options;
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
  } catch (audioError) {
    resolvedAudioUrl = null;
  }

  const assistantEntry = appendMessage("assistant", data.reply, {
    intent: data.intent,
    source: data.source,
    audioUrl: resolvedAudioUrl,
    latencyMs,
  });
  state.lastAssistantReplyText = data.reply || "";

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

async function requestClassicChatMessage(message) {
  const { response, data } = await fetchJson(
    "/chat",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    },
    CHAT_REQUEST_TIMEOUT_MS
  );

  if (!response.ok) {
    throw new Error(data.detail || "ส่งข้อความไม่สำเร็จ");
  }
  return data;
}

async function handleStreamingChatMessage(message, options = {}) {
  const { latencyStartedAt = performance.now() } = options;
  let streamedText = "";
  let assistantEntry = null;

  try {
    assistantEntry = appendStreamingAssistantMessage();
    const finalData = await fetchChatStream(message, {
      onStatus: (statusText) => {
        if (statusText) {
          setChatLoadingText(statusText);
        }
      },
      onChunk: (chunk) => {
        streamedText += chunk;
        updateAssistantEntryText(assistantEntry, streamedText);
      },
    });

    await finalizeAssistantEntry(assistantEntry, finalData, {
      latencyMs: performance.now() - latencyStartedAt,
    });
    setPillState(chatStatus, "good", "ตอบแล้ว");
    if (finalData.intent === "weather_query") {
      weatherResult.textContent = finalData.reply;
      weatherResult.classList.remove("muted");
    }
    await refreshDashboardStatus();
    await refreshVoiceDebugStatus();
    return assistantEntry;
  } catch (error) {
    if (assistantEntry) {
      assistantEntry.wrapper.remove();
    }
    throw error;
  }
}

function stopAllVoiceCapture() {
  clearAutoListenTimer();
  clearWakeListenWatchdog();
  clearSpeechRecognitionTimeout();
  clearVoiceLoopRestartTimer();

  if (state.speechRecognition) {
    detachSpeechRecognition(state.speechRecognition);
    try {
      state.speechRecognition.abort();
    } catch (error) {
      // Chrome may already have closed this recognition cycle.
    }
    state.speechRecognition = null;
  }

  if (state.mediaRecorder && state.mediaRecorder.state !== "inactive") {
    state.discardCurrentRecording = true;
    state.mediaRecorder.stop();
  }

  cleanupMediaStream();
  state.recording = false;
  state.wakeListening = false;
  state.recognitionMode = null;
  chatMicButton.textContent = "Start talking";
}

function stopCurrentVoiceTurn(options = {}) {
  if (isMediaRecorderActive()) {
    const discard = Boolean(options.discard);
    setMicStatus(discard ? "ยังไม่ได้ยินเสียงชัด กำลังลองฟังใหม่..." : "รับเสียงแล้ว กำลังส่งให้ AI...", "busy");
    clearVoiceRecordingMonitors();
    state.discardCurrentRecording = discard;
    state.mediaRecorder.stop();
    return true;
  }

  if (state.speechRecognition) {
    try {
      state.speechRecognition.stop();
      setMicStatus("รับเสียงแล้ว กำลังประมวลผล...", "busy");
      return true;
    } catch (error) {
      return false;
    }
  }

  return false;
}

function setupAutoStopRecording(stream) {
  const AudioContextConstructor = window.AudioContext || window.webkitAudioContext;
  const recorder = state.mediaRecorder;
  if (!AudioContextConstructor || !recorder) {
    state.voiceRecordTimeoutId = window.setTimeout(stopCurrentVoiceTurn, VOICE_RECORD_MAX_MS);
    return;
  }

  const audioContext = new AudioContextConstructor();
  const source = audioContext.createMediaStreamSource(stream);
  const analyser = audioContext.createAnalyser();
  analyser.fftSize = 1024;
  source.connect(analyser);
  state.audioContext = audioContext;
  state.audioAnalyser = analyser;
  void audioContext.resume?.().catch(() => {});

  const samples = new Uint8Array(analyser.fftSize);
  const startedAt = performance.now();
  let heardSpeech = false;
  let lastVoiceAt = startedAt;

  const tick = () => {
    if (!state.mediaRecorder || state.mediaRecorder.state !== "recording") {
      return;
    }

    analyser.getByteTimeDomainData(samples);
    let sumSquares = 0;
    for (const sample of samples) {
      const normalized = (sample - 128) / 128;
      sumSquares += normalized * normalized;
    }

    const rms = Math.sqrt(sumSquares / samples.length);
    const now = performance.now();
    if (rms >= VOICE_SPEECH_RMS_THRESHOLD) {
      heardSpeech = true;
      lastVoiceAt = now;
    }

    const elapsedMs = now - startedAt;
    const canStop = elapsedMs >= VOICE_RECORD_MIN_MS;
    const silenceReached = heardSpeech && now - lastVoiceAt >= VOICE_SILENCE_STOP_MS;
    const noSpeechReached = !heardSpeech && elapsedMs >= VOICE_NO_SPEECH_TIMEOUT_MS;
    const maxReached = elapsedMs >= VOICE_RECORD_MAX_MS;

    if (canStop && noSpeechReached) {
      stopCurrentVoiceTurn({ discard: true });
      return;
    }

    if (canStop && (silenceReached || maxReached)) {
      stopCurrentVoiceTurn();
      return;
    }

    state.voiceRecordAnimationId = window.requestAnimationFrame(tick);
  };

  state.voiceRecordTimeoutId = window.setTimeout(stopCurrentVoiceTurn, VOICE_RECORD_MAX_MS + 500);
  state.voiceRecordAnimationId = window.requestAnimationFrame(tick);
}

async function maybeContinueListening(assistantEntry) {
  clearAutoListenTimer();

  if (state.stopRequested) {
    state.conversationActive = false;
    state.keepMicOpen = false;
    setVoiceLifecycleState(VOICE_STATE_STOPPED);
    return;
  }

  await waitForAssistantPlayback(assistantEntry);

  if (state.keepMicOpen) {
    state.conversationActive = true;
    setVoiceLifecycleState(VOICE_STATE_ACTIVE);
    setMicStatus("รอเสียงตกค้างสั้น ๆ แล้วจะฟังต่อ...", "live");
    if (state.voiceMode === "wake") {
      restartSpeechRecognitionLoop(POST_SPEAKING_COOLDOWN_MS);
      return;
    }
    state.autoListenTimerId = window.setTimeout(() => {
      state.autoListenTimerId = null;
      startActiveConversationTurn();
    }, POST_SPEAKING_COOLDOWN_MS);
    return;
  }

  state.conversationActive = false;
  if (state.voiceMode === "wake") {
    scheduleWakeWordResume();
  } else {
    setVoiceLifecycleState(VOICE_STATE_STOPPED);
    setMicStatus("พร้อมเริ่มรอบใหม่เมื่อกด Start talking");
  }
}

async function handleVoiceTurnResponse(payload) {
  const data = normalizeVoicePayload(payload);
  const keepOpen = !isExitPhrase(data.heard_text || "") && Boolean(data.keep_mic_open);
  resetActiveListenRetries();

  if (data.heard_text) {
    rememberHandledTranscript(data.heard_text);
    appendMessage("user", data.heard_text);
    showHeardText(data.heard_text);
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
    action: data.action,
    keepMicOpen: keepOpen,
    audioUrl: resolvedAudioUrl,
  });

  state.lastAssistantReplyText = data.reply || "";
  state.conversationActive = keepOpen;
  setVoiceLifecycleState(
    keepOpen ? VOICE_STATE_ACTIVE : state.voiceMode === "wake" ? VOICE_STATE_IDLE_WAKE : VOICE_STATE_STOPPED
  );
  setKeepMicIndicator(
    keepOpen,
    keepOpen ? "ระบบจะฟังต่อรอบถัดไป" : "จบคำตอบรอบนี้แล้ว"
  );
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

  const apiMessage = buildChatApiMessage(trimmed);
  const isThinkingMode = shouldUseThinkingModeForMessage(trimmed);
  const chatStartedAt = performance.now();
  const shouldResumeWakeAfterText = state.voiceMode === "wake" && !state.stopRequested;
  appendMessage("user", trimmed, {
    mode: isThinkingMode ? CHAT_MODE_THINKING : CHAT_MODE_FAST,
  });
  chatInput.value = "";
  showHeardText("");
  setChatBusy(true);
  state.stopRequested = !shouldResumeWakeAfterText;
  state.conversationActive = false;
  setKeepMicIndicator(false, "โหมดแชตข้อความปิด loop เสียงไว้ก่อน");
  stopAllVoiceCapture();
  if (shouldResumeWakeAfterText) {
    state.stopRequested = false;
  }
  startChatWaitHints(isThinkingMode);

  try {
    try {
      await handleStreamingChatMessage(apiMessage, { latencyStartedAt: chatStartedAt });
    } catch (streamError) {
      const data = await requestClassicChatMessage(apiMessage);
      await handleChatResponse(data, {
        appendUserMessage: false,
        userMessage: trimmed,
        latencyMs: performance.now() - chatStartedAt,
      });
    }
  } catch (error) {
    appendMessage("assistant", getReadableErrorMessage(error, "เกิดปัญหาระหว่างส่งข้อความ ลองใหม่อีกครั้งได้ไหม"), {
      source: "fallback",
    });
    setPillState(chatStatus, "bad", "เกิดข้อผิดพลาด");
  } finally {
    clearChatWaitHints();
    setChatLoadingText("AI กำลังตอบ...");
    setChatBusy(false);
    if (shouldResumeWakeAfterText && !state.stopRequested) {
      keepWakeWordModeAlive("พิมพ์แชตเสร็จแล้ว กลับไปรอฟังคำว่า น้องฟ้า", 300);
    } else {
      setVoiceLifecycleState(
        state.voiceMode === "wake" && !state.stopRequested ? VOICE_STATE_IDLE_WAKE : VOICE_STATE_STOPPED
      );
    }
  }
}

async function sendVoiceText(message) {
  const trimmed = message.trim();
  if (!trimmed || state.chatBusy) {
    return;
  }
  if (isLikelyAssistantEcho(trimmed)) {
    scheduleActiveConversationRetry("ได้ยินเหมือนเป็นเสียงตอบกลับของระบบ กำลังฟังใหม่...");
    return;
  }

  state.voiceRequestActive = true;
  if (state.recognitionMode === "loop") {
    pauseSpeechRecognitionLoop();
  }
  clearAutoListenTimer();
  setChatBusy(true);
  setVoiceSessionState("processing");
  setChatLoadingText("รับคำสั่งแล้ว AI กำลังตอบ...");
  setMicStatus("รับคำพูดแล้ว กำลังให้ AI ตอบ...", "busy");
  showHeardText(trimmed);

  const formData = new FormData();
  formData.append("message", trimmed);
  formData.append("pir_state", String(currentPirState()));

  let handledResponse = false;
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
    handledResponse = true;
    setMicStatus("ตอบกลับด้วยเสียงแล้ว", "busy");
  } catch (error) {
    const messageText = getReadableErrorMessage(error, "เกิดปัญหาระหว่างส่งข้อความเสียง ลองใหม่อีกครั้งได้ไหม");
    appendMessage("assistant", messageText, { source: "fallback" });
    setPillState(chatStatus, "bad", "เกิดข้อผิดพลาด");
    setKeepMicIndicator(false, "ปิดไมค์ต่อเนื่องชั่วคราวเพราะเกิดข้อผิดพลาด");
    state.conversationActive = false;
    setMicStatus(messageText, "busy");
  } finally {
    state.voiceRequestActive = false;
    setChatBusy(false);
    if (!handledResponse && !state.recording && !state.wakeListening && !state.conversationActive) {
      if (keepWakeWordModeAlive("เกิดปัญหารอบนี้ แต่ยังรอฟัง น้องฟ้า ต่อ", 700)) {
        return;
      }
      setVoiceLifecycleState(state.voiceMode === "wake" ? VOICE_STATE_IDLE_WAKE : VOICE_STATE_STOPPED);
    }
  }
}

async function sendVoiceRecording(audioBlob, mimeType) {
  if (!audioBlob.size) {
    setMicStatus("ไม่ได้รับข้อมูลเสียง ลองกด Start talking ใหม่อีกครั้ง", "busy");
    if (scheduleActiveConversationRetry("ไม่ได้รับข้อมูลเสียง กำลังเปิดไมค์ลองใหม่...")) {
      return;
    }
    return;
  }

  state.voiceRequestActive = true;
  setChatBusy(true);
  setVoiceSessionState("processing");
  setChatLoadingText("รับเสียงแล้ว AI กำลังตอบ...");
  setMicStatus("กำลังแปลงเสียงเป็นข้อความ...", "busy");
  showHeardText("");

  const extension = mimeType.includes("ogg") ? "ogg" : mimeType.includes("mp4") ? "m4a" : "webm";
  const formData = new FormData();
  formData.append("audio", audioBlob, `voice-input.${extension}`);
  formData.append("pir_state", String(currentPirState()));

  let handledResponse = false;
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
    handledResponse = true;
    setMicStatus("ตอบกลับด้วยเสียงแล้ว", "busy");
  } catch (error) {
    const messageText = getReadableErrorMessage(error, "เกิดปัญหาระหว่างส่งเสียง ลองใหม่อีกครั้งได้ไหม");
    appendMessage("assistant", messageText, { source: "fallback" });
    setPillState(chatStatus, "bad", "เกิดข้อผิดพลาด");
    setKeepMicIndicator(false, "ปิดไมค์ต่อเนื่องชั่วคราวเพราะเกิดข้อผิดพลาด");
    state.conversationActive = false;
    setMicStatus(messageText, "busy");
  } finally {
    state.voiceRequestActive = false;
    setChatBusy(false);
    if (!handledResponse && !state.recording && !state.wakeListening && !state.conversationActive) {
      if (keepWakeWordModeAlive("เกิดปัญหารอบนี้ แต่ยังรอฟัง น้องฟ้า ต่อ", 700)) {
        return;
      }
      setVoiceLifecycleState(state.voiceMode === "wake" ? VOICE_STATE_IDLE_WAKE : VOICE_STATE_STOPPED);
    }
  }
}

async function startTurnRecognition() {
  if (state.speechRecognition) {
    return false;
  }

  const recognition = createSpeechRecognition("turn");
  if (!recognition) {
    return false;
  }

  try {
    let turnFinished = false;
    const clearTurnRecognition = () => {
      clearSpeechRecognitionTimeout();
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.onend = null;
      recognition.onnomatch = null;
      recognition.onspeechend = null;
      state.recording = false;
      clearSpeechRecognitionIfCurrent(recognition);
    };

    state.speechRecognition = recognition;
    state.recording = true;
    state.wakeListening = false;
    chatMicButton.textContent = "Stop";
    setVoiceLifecycleState(VOICE_STATE_ACTIVE);
    setMicStatus("กำลังฟังคำสั่งหรือคำถามอยู่ พูดได้เลย", "live");
    setChatBusy(false);
    state.speechRecognitionTimeoutId = window.setTimeout(() => {
      if (turnFinished || state.speechRecognition !== recognition) {
        return;
      }
      turnFinished = true;
      clearTurnRecognition();
      try {
        recognition.abort();
      } catch (error) {
        // Browser may already have closed this recognition turn.
      }
      chatMicButton.textContent = "Start talking";
      setChatBusy(false);
      if (scheduleActiveConversationRetry("ไมค์ค้างนานเกินไป กำลังเปิดไมค์ใหม่ให้...")) {
        return;
      }
      setVoiceLifecycleState(state.voiceMode === "wake" ? VOICE_STATE_IDLE_WAKE : VOICE_STATE_STOPPED);
      setMicStatus("ไมค์รอบนี้ไม่ส่งผลลัพธ์ กลับไปรอฟังคำว่า น้องฟ้า", "busy");
    }, SPEECH_RECOGNITION_TURN_TIMEOUT_MS);

    recognition.onresult = async (event) => {
      if (turnFinished) {
        return;
      }
      turnFinished = true;
      const transcript = Array.from(event.results || [])
        .map((result) => result[0]?.transcript || "")
        .join(" ")
        .trim();

      clearTurnRecognition();

      if (!transcript) {
        chatMicButton.textContent = "Start talking";
        setChatBusy(false);
        if (scheduleActiveConversationRetry("ยังจับคำพูดไม่ได้ชัด กำลังลองฟังอีกครั้ง...")) {
          return;
        }
        setMicStatus("ยังจับคำพูดไม่ได้ชัด ลองใหม่อีกครั้งได้", "busy");
        return;
      }

      if (isDuplicateTranscript(transcript)) {
        chatMicButton.textContent = "Start talking";
        setChatBusy(false);
        scheduleActiveConversationRetry("ได้ยินข้อความเดิมซ้ำ กำลังฟังใหม่อีกครั้ง...");
        return;
      }

      if (isLikelyAssistantEcho(transcript)) {
        chatMicButton.textContent = "Start talking";
        setChatBusy(false);
        scheduleActiveConversationRetry("ได้ยินเหมือนเป็นเสียงตอบกลับของระบบ กำลังฟังใหม่...");
        return;
      }

      if (isExitPhrase(transcript)) {
        state.conversationActive = false;
      }

      resetActiveListenRetries();
      chatMicButton.textContent = "กำลังตอบ...";
      await sendVoiceText(transcript);
    };

    recognition.onnomatch = () => {
      if (turnFinished) {
        return;
      }
      turnFinished = true;
      clearTurnRecognition();
      chatMicButton.textContent = "Start talking";
      setChatBusy(false);
      if (scheduleActiveConversationRetry("ยังแปลงเสียงเป็นข้อความไม่ได้ กำลังเปิดไมค์ลองใหม่...")) {
        return;
      }
      setMicStatus("ยังแปลงเสียงเป็นข้อความไม่ได้ ลองพูดอีกครั้งได้", "busy");
    };

    recognition.onerror = () => {
      if (turnFinished) {
        return;
      }
      turnFinished = true;
      clearTurnRecognition();
      chatMicButton.textContent = "Start talking";
      setChatBusy(false);
      if (scheduleActiveConversationRetry("ฟังเสียงสะดุดนิดหน่อย กำลังเปิดไมค์ใหม่...")) {
        return;
      }
      setKeepMicIndicator(false, "ฟังเสียงไม่สำเร็จ");
      state.conversationActive = false;
      if (state.voiceMode === "wake") {
        scheduleWakeWordResume();
      } else {
        setVoiceLifecycleState(VOICE_STATE_STOPPED);
      }
      setMicStatus("ฟังเสียงไม่สำเร็จ ลองใหม่อีกครั้งได้", "busy");
    };

    recognition.onend = () => {
      if (turnFinished) {
        return;
      }
      turnFinished = true;
      clearTurnRecognition();
      chatMicButton.textContent = "Start talking";
      setChatBusy(false);
      if (scheduleActiveConversationRetry("ยังไม่ได้ยินคำถามชัด ๆ กำลังเปิดไมค์ต่อให้อีกครั้ง...")) {
        return;
      }
      setVoiceLifecycleState(state.voiceMode === "wake" ? VOICE_STATE_IDLE_WAKE : VOICE_STATE_STOPPED);
    };

    recognition.start();
    return true;
  } catch (error) {
    state.recording = false;
    state.speechRecognition = null;
    chatMicButton.textContent = "Start talking";
    setChatBusy(false);
    setVoiceLifecycleState(VOICE_STATE_STOPPED);
    setMicStatus("เปิดโหมดฟังเสียงในเบราว์เซอร์ไม่สำเร็จ จะใช้อัปโหลดเสียงแทน", "busy");
    return false;
  }
}

function startWakeWordListening() {
  return startSpeechRecognitionLoop();
}

async function startActiveConversationTurn() {
  if (state.chatBusy || state.recording || state.stopRequested) {
    return;
  }

  if (state.voiceMode === "wake") {
    state.stopRequested = false;
    state.conversationActive = true;
    setVoiceLifecycleState(VOICE_STATE_ACTIVE);
    return startSpeechRecognitionLoop();
  }

  state.stopRequested = false;
  state.conversationActive = true;
  setVoiceLifecycleState(VOICE_STATE_ACTIVE);
  setMicStatus("กำลังเปิดไมค์สำหรับรอบถัดไป...", "live");

  if (browserSupportsSpeechRecognition()) {
    const startedBrowserRecognition = await startTurnRecognition();
    if (startedBrowserRecognition) {
      return;
    }
  }

  if (!browserSupportsRecording()) {
    setMicStatus("เบราว์เซอร์นี้ยังไม่รองรับการอัดเสียงสำหรับเดโมนี้", "busy");
    state.conversationActive = false;
    setVoiceLifecycleState(VOICE_STATE_STOPPED);
    return;
  }

  const mimeType = getSupportedRecordingMimeType();
  if (!mimeType) {
    setMicStatus("เบราว์เซอร์นี้ยังไม่รองรับรูปแบบไฟล์เสียงที่ใช้งานได้", "busy");
    state.conversationActive = false;
    setVoiceLifecycleState(VOICE_STATE_STOPPED);
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
    state.discardCurrentRecording = false;
    state.recording = true;
    chatMicButton.textContent = "Stop";
    setVoiceLifecycleState(VOICE_STATE_ACTIVE);
    setMicStatus("กำลังฟังอยู่ พูดได้เลย ระบบจะส่งให้ AI เมื่อพูดจบ", "live");

    state.mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data && event.data.size > 0) {
        state.audioChunks.push(event.data);
      }
    });

    state.mediaRecorder.addEventListener("stop", async () => {
      const shouldDiscard = state.discardCurrentRecording;
      state.discardCurrentRecording = false;
      const recordedBlob = new Blob(state.audioChunks, { type: mimeType });
      cleanupMediaStream();
      state.recording = false;
      chatMicButton.textContent = "Start talking";
      setChatBusy(false);
      if (shouldDiscard) {
        if (!state.stopRequested && state.conversationActive) {
          scheduleActiveConversationRetry("ยังไม่ได้ยินเสียงชัด กำลังเปิดไมค์ลองใหม่...");
        }
        return;
      }
      await sendVoiceRecording(recordedBlob, mimeType);
    });

    state.mediaRecorder.start();
    setupAutoStopRecording(stream);
    setChatBusy(false);
  } catch (error) {
    cleanupMediaStream();
    state.recording = false;
    chatMicButton.textContent = "Start talking";
    setChatBusy(false);
    state.conversationActive = false;
    setVoiceLifecycleState(VOICE_STATE_STOPPED);
    setMicStatus(
      getReadableErrorMessage(error, "เปิดไมโครโฟนไม่สำเร็จ ลองเช็ก permission ของเบราว์เซอร์"),
      "busy"
    );
  }
}

async function startVoiceInteraction() {
  clearAutoListenTimer();
  state.stopRequested = false;

  if (state.voiceMode === "wake" && !state.conversationActive) {
    state.conversationActive = true;
    setVoiceLifecycleState(VOICE_STATE_ACTIVE);
    voiceTurnStatus.textContent = "เริ่มคุยโดยไม่ต้องพูด wake word รอบนี้";
  }
  await startActiveConversationTurn();
}

function stopVoiceInteraction() {
  state.stopRequested = true;
  state.conversationActive = false;
  state.wakeListening = false;
  resetActiveListenRetries();
  setKeepMicIndicator(false, "หยุดโหมดเสียงแล้ว");
  clearAutoListenTimer();
  clearWakeListenWatchdog();
  stopAllVoiceCapture();
  setVoiceLifecycleState(VOICE_STATE_STOPPED);
  setMicStatus("ปิดไมค์แล้ว กด Start talking หรือเปิด Wake Word ใหม่ได้", "busy");
}

function setVoiceMode(mode) {
  if (mode === state.voiceMode) {
    if (
      mode === "wake" &&
      !state.chatBusy &&
      !state.recording &&
      !state.wakeListening &&
      !state.speechRecognition
    ) {
      state.stopRequested = false;
      startWakeWordListening();
    }
    return;
  }

  state.voiceMode = mode;
  state.conversationActive = false;
  state.keepMicOpen = false;
  state.stopRequested = false;
  resetActiveListenRetries();
  clearAutoListenTimer();
  stopAllVoiceCapture();
  updateVoiceModeButtons();

  if (mode === "wake") {
    if (!browserSupportsSpeechRecognition()) {
      setMicStatus("Wake Word Mode ต้องใช้ Chrome หรือ Edge ที่รองรับ speech recognition", "busy");
      setVoiceLifecycleState(VOICE_STATE_STOPPED);
      voiceTurnStatus.textContent = "Wake Word Mode ยังไม่พร้อมในเบราว์เซอร์นี้";
      return;
    }
    setKeepMicIndicator(false, "กำลังรอฟังคำว่า น้องฟ้า");
    voiceTurnStatus.textContent = "Wake Word Mode พร้อมใช้งาน พูดว่า 'น้องฟ้า' ได้เลย";
    startWakeWordListening();
    return;
  }

  setVoiceLifecycleState(VOICE_STATE_STOPPED);
  setKeepMicIndicator(false, "Push-to-Talk Mode พร้อมแล้ว");
  setMicStatus("โหมดกดคุยพร้อมใช้งาน กด Start talking เมื่อต้องการคุย");
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await sendChatMessage(chatInput.value);
});

chatMicButton.addEventListener("click", async () => {
  if (state.recording) {
    if (stopCurrentVoiceTurn()) {
      return;
    }
    stopVoiceInteraction();
    return;
  }
  await startVoiceInteraction();
});

chatStopButton.addEventListener("click", () => {
  stopVoiceInteraction();
});

voiceModePushButton.addEventListener("click", () => {
  setVoiceMode("push");
});

voiceModeWakeButton.addEventListener("click", () => {
  setVoiceMode("wake");
});

chatModeFastButton.addEventListener("click", () => {
  setChatResponseMode(CHAT_MODE_FAST);
});

chatModeThinkingButton.addEventListener("click", () => {
  setChatResponseMode(CHAT_MODE_THINKING);
});

quickActions.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-message]");
  if (!button || button.disabled) {
    return;
  }
  await sendChatMessage(button.dataset.message || "");
});

thinkingTestActions.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-test-message]");
  if (!button || button.disabled) {
    return;
  }
  setChatResponseMode(button.dataset.testMode || CHAT_MODE_FAST);
  await sendChatMessage(button.dataset.testMessage || "");
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
llmWarmupButton.addEventListener("click", warmupLlm);
llmSleepButton.addEventListener("click", sleepLlm);
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
  if (!state.chatBusy && !state.recording && !state.wakeListening) {
    setPillState(chatStatus, "neutral", "พร้อมใช้งาน");
  }
});

window.addEventListener("offline", () => {
  setPillState(chatStatus, "bad", "ออฟไลน์");
});

window.addEventListener("beforeunload", () => {
  clearAutoListenTimer();
  clearWakeListenWatchdog();
  clearSpeechRecognitionTimeout();
  clearVoiceLoopRestartTimer();
  stopAllVoiceCapture();
  for (const audioElement of document.querySelectorAll("audio")) {
    revokeAudioObjectUrl(audioElement);
  }
});

appendMessage(
  "assistant",
  "พร้อมทดสอบแล้ว ลองกดปุ่มตัวอย่าง พิมพ์ข้อความ หรือสลับเป็น Wake Word Mode แล้วพูดว่า น้องฟ้า ได้เลย",
  { source: "placeholder" }
);

if (browserSupportsSpeechRecognition()) {
  setMicStatus("ไมโครโฟนพร้อมใช้งาน รองรับทั้ง Push-to-Talk และ Wake Word Mode");
} else if (browserSupportsRecording()) {
  setMicStatus("ไมโครโฟนพร้อมใช้งานแบบกดคุย แต่ Wake Word Mode ต้องใช้ browser speech recognition", "busy");
} else {
  setMicStatus("เบราว์เซอร์นี้ยังไม่รองรับการอัดเสียงสำหรับเดโมนี้", "busy");
  chatMicButton.disabled = true;
  voiceModeWakeButton.disabled = true;
}

updateVoiceModeButtons();
updateChatResponseModeButtons();
setVoiceLifecycleState(VOICE_STATE_STOPPED);
setKeepMicIndicator(false, "Push-to-Talk Mode พร้อมแล้ว");
setPillState(chatStatus, "neutral", "พร้อมใช้งาน");
setChatBusy(false);
refreshDashboardStatus();
refreshVoiceDebugStatus();
window.setInterval(refreshDashboardStatus, 15000);
window.setInterval(refreshVoiceDebugStatus, 5000);
