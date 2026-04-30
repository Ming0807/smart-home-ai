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
