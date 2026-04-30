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

function updateVoiceModeButtons() {
  voiceModePushButton.classList.toggle("active", state.voiceMode === "push");
  voiceModeWakeButton.classList.toggle("active", state.voiceMode === "wake");
  chatMicButton.textContent = "Start talking";
}

function shouldUseThinkingModeForMessage(message) {
  return state.chatResponseMode === CHAT_MODE_THINKING || messageHasThinkingTrigger(message);
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
