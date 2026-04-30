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
