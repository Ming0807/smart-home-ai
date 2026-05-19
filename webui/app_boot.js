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

sensorRefreshButton.addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  void refreshDashboardStatus();
});
motionRefreshButton.addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  void refreshDashboardStatus();
});
voiceNodeRefreshButton?.addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  void refreshVoiceNodePanel();
});

let voiceNodeAutoWakeAttempted = false;

async function maybeStartVoiceNodeWakeOnLoad() {
  if (voiceNodeAutoWakeAttempted) {
    return;
  }
  voiceNodeAutoWakeAttempted = true;

  try {
    const nodeStatus = await fetchVoiceNodeStatus();
    const shouldStartWake =
      nodeStatus?.online &&
      !nodeStatus.wake_mode_enabled &&
      !nodeStatus.conversation_mode_enabled &&
      !nodeStatus.pending_command_count;

    if (!shouldStartWake) {
      return;
    }

    if (voiceNodeRefreshStatus) {
      voiceNodeRefreshStatus.textContent = "เปิด Wake บอร์ดให้อัตโนมัติแล้ว เรียก น้องฟ้า ได้เลย";
    }
    await queueVoiceNodeWakeListenStart();
    await refreshVoiceNodePanel();
  } catch (error) {
    if (voiceNodeRefreshStatus) {
      voiceNodeRefreshStatus.textContent = getReadableErrorMessage(
        error,
        "เปิด Wake อัตโนมัติไม่สำเร็จ กดเปิด Wake บอร์ดเองได้"
      );
    }
  }
}

voiceNodeSpeakerTestButton?.addEventListener("click", async (event) => {
  event.preventDefault();
  event.stopPropagation();
  voiceNodeSpeakerTestButton.disabled = true;
  if (voiceNodeRefreshStatus) {
    voiceNodeRefreshStatus.textContent = "ส่งคำสั่งทดสอบลำโพงแล้ว รอบอร์ด polling...";
  }
  try {
    await queueVoiceNodeSpeakerTest();
    await refreshVoiceNodePanel();
  } catch (error) {
    if (voiceNodeRefreshStatus) {
      voiceNodeRefreshStatus.textContent = getReadableErrorMessage(error, "ส่งคำสั่งทดสอบลำโพงไม่สำเร็จ");
    }
  } finally {
    voiceNodeSpeakerTestButton.disabled = false;
  }
});
voiceNodeSpeechTestButton?.addEventListener("click", async (event) => {
  event.preventDefault();
  event.stopPropagation();
  voiceNodeSpeechTestButton.disabled = true;
  if (voiceNodeRefreshStatus) {
    voiceNodeRefreshStatus.textContent = "กำลังสร้างเสียงพูดและส่งให้บอร์ดเล่นแบบ streaming...";
  }
  try {
    await queueVoiceNodeSpeechTest();
    window.setTimeout(() => void refreshVoiceNodePanel(), 2500);
  } catch (error) {
    if (voiceNodeRefreshStatus) {
      voiceNodeRefreshStatus.textContent = getReadableErrorMessage(error, "สั่งทดสอบเสียงพูดไม่สำเร็จ");
    }
  } finally {
    voiceNodeSpeechTestButton.disabled = false;
  }
});
voiceNodeRecordOnceButton?.addEventListener("click", async (event) => {
  event.preventDefault();
  event.stopPropagation();
  voiceNodeRecordOnceButton.disabled = true;
  if (voiceNodeRefreshStatus) {
    voiceNodeRefreshStatus.textContent = "ส่งคำสั่งให้อัดเสียง 1 รอบแล้ว รอดูผลล่าสุด...";
  }
  try {
    const expectedText = voiceNodeExpectedText ? voiceNodeExpectedText.value.trim() : "";
    await queueVoiceNodeRecordOnce(expectedText);
    state.voiceNodeRecordPendingSince = Date.now();
    window.setTimeout(() => {
      if (state.voiceNodeRecordPendingSince && Date.now() - state.voiceNodeRecordPendingSince >= 11000) {
        state.voiceNodeRecordPendingSince = 0;
        if (voiceNodeRecordOnceButton) {
          voiceNodeRecordOnceButton.disabled = false;
        }
        if (voiceNodeRefreshStatus) {
          voiceNodeRefreshStatus.textContent = "record command timeout; refresh and try again if the board did not upload";
        }
      }
    }, 12000);
    await refreshVoiceNodePanel();
  } catch (error) {
    if (voiceNodeRefreshStatus) {
      voiceNodeRefreshStatus.textContent = getReadableErrorMessage(error, "ส่งคำสั่งอัดเสียงไม่สำเร็จ");
    }
  } finally {
    if (!state.voiceNodeRecordPendingSince) {
      voiceNodeRecordOnceButton.disabled = false;
    }
  }
});
voiceNodeConversationStartButton?.addEventListener("click", async (event) => {
  event.preventDefault();
  event.stopPropagation();
  voiceNodeConversationStartButton.disabled = true;
  if (voiceNodeRefreshStatus) {
    voiceNodeRefreshStatus.textContent = "สั่งให้บอร์ดเริ่มคุยต่อเนื่องแล้ว รอเสียงติ๊ดแล้วพูดได้เลย";
  }
  try {
    await queueVoiceNodeConversationStart();
    await refreshVoiceNodePanel();
  } catch (error) {
    if (voiceNodeRefreshStatus) {
      voiceNodeRefreshStatus.textContent = getReadableErrorMessage(error, "เริ่มคุยผ่านบอร์ดไม่สำเร็จ");
    }
  } finally {
    voiceNodeConversationStartButton.disabled = false;
  }
});
voiceNodeConversationStopButton?.addEventListener("click", async (event) => {
  event.preventDefault();
  event.stopPropagation();
  voiceNodeConversationStopButton.disabled = true;
  if (voiceNodeRefreshStatus) {
    voiceNodeRefreshStatus.textContent = "ส่งคำสั่งหยุดคุยผ่านบอร์ดแล้ว";
  }
  try {
    await queueVoiceNodeConversationStop();
    await refreshVoiceNodePanel();
  } catch (error) {
    if (voiceNodeRefreshStatus) {
      voiceNodeRefreshStatus.textContent = getReadableErrorMessage(error, "หยุดคุยผ่านบอร์ดไม่สำเร็จ");
    }
  } finally {
    voiceNodeConversationStopButton.disabled = false;
  }
});
voiceNodeWakeStartButton?.addEventListener("click", async (event) => {
  event.preventDefault();
  event.stopPropagation();
  voiceNodeWakeStartButton.disabled = true;
  if (voiceNodeRefreshStatus) {
    voiceNodeRefreshStatus.textContent = "สั่งให้บอร์ดรอฟังคำปลุก สวัสดีน้องฟ้า แล้ว";
  }
  try {
    await queueVoiceNodeWakeListenStart();
    await refreshVoiceNodePanel();
  } catch (error) {
    if (voiceNodeRefreshStatus) {
      voiceNodeRefreshStatus.textContent = getReadableErrorMessage(error, "เปิด Wake บอร์ดไม่สำเร็จ");
    }
  } finally {
    voiceNodeWakeStartButton.disabled = false;
  }
});
voiceNodeWakeStopButton?.addEventListener("click", async (event) => {
  event.preventDefault();
  event.stopPropagation();
  voiceNodeWakeStopButton.disabled = true;
  if (voiceNodeRefreshStatus) {
    voiceNodeRefreshStatus.textContent = "ส่งคำสั่งปิด Wake บอร์ดแล้ว";
  }
  try {
    await queueVoiceNodeWakeListenStop();
    await refreshVoiceNodePanel();
  } catch (error) {
    if (voiceNodeRefreshStatus) {
      voiceNodeRefreshStatus.textContent = getReadableErrorMessage(error, "ปิด Wake บอร์ดไม่สำเร็จ");
    }
  } finally {
    voiceNodeWakeStopButton.disabled = false;
  }
});
voiceNodeStreamTestButton?.addEventListener("click", async (event) => {
  event.preventDefault();
  event.stopPropagation();
  voiceNodeStreamTestButton.disabled = true;
  if (voiceNodeRefreshStatus) {
    voiceNodeRefreshStatus.textContent = "ส่งคำสั่ง PCM stream test แล้ว รอดู Stream stats...";
  }
  try {
    await queueVoiceNodeStreamTestStart();
    await refreshVoiceNodePanel();
    window.setTimeout(() => void refreshVoiceNodePanel(), 2500);
    window.setTimeout(() => void refreshVoiceNodePanel(), 6500);
  } catch (error) {
    if (voiceNodeRefreshStatus) {
      voiceNodeRefreshStatus.textContent = getReadableErrorMessage(error, "ส่งคำสั่ง PCM stream test ไม่สำเร็จ");
    }
  } finally {
    voiceNodeStreamTestButton.disabled = false;
  }
});
voiceNodeStreamProcessButton?.addEventListener("click", async (event) => {
  event.preventDefault();
  event.stopPropagation();
  voiceNodeStreamProcessButton.disabled = true;
  if (voiceNodeRefreshStatus) {
    voiceNodeRefreshStatus.textContent = "ส่งคำสั่ง PCM STT test แล้ว รอเสียงติ๊ดจบสักครู่ จากนั้นพูดภายใน 7 วินาที...";
  }
  try {
    await queueVoiceNodeStreamProcessStart();
    await refreshVoiceNodePanel();
    window.setTimeout(() => void refreshVoiceNodePanel(), 7000);
    window.setTimeout(() => void refreshVoiceNodePanel(), 12000);
    window.setTimeout(() => void refreshVoiceNodePanel(), 22000);
  } catch (error) {
    if (voiceNodeRefreshStatus) {
      voiceNodeRefreshStatus.textContent = getReadableErrorMessage(error, "ส่งคำสั่ง PCM STT test ไม่สำเร็จ");
    }
  } finally {
    voiceNodeStreamProcessButton.disabled = false;
  }
});
voiceNodeClearHistoryButton?.addEventListener("click", async (event) => {
  event.preventDefault();
  event.stopPropagation();
  voiceNodeClearHistoryButton.disabled = true;
  if (voiceNodeRefreshStatus) {
    voiceNodeRefreshStatus.textContent = "กำลังล้างประวัติทดสอบเสียง...";
  }
  try {
    await clearVoiceNodeAudioHistory();
    state.voiceNodeRecordPendingSince = 0;
    if (voiceNodeRecordOnceButton) {
      voiceNodeRecordOnceButton.disabled = false;
    }
    await refreshVoiceNodePanel();
    if (voiceNodeRefreshStatus) {
      voiceNodeRefreshStatus.textContent = "ล้างประวัติแล้ว เริ่มเทสรอบใหม่ได้เลย";
    }
  } catch (error) {
    if (voiceNodeRefreshStatus) {
      voiceNodeRefreshStatus.textContent = getReadableErrorMessage(error, "ล้างประวัติไม่สำเร็จ");
    }
  } finally {
    voiceNodeClearHistoryButton.disabled = false;
  }
});
voiceNodeTuningForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  event.stopPropagation();
  const submitButton = voiceNodeTuningForm.querySelector("button[type='submit']");
  if (submitButton) {
    submitButton.disabled = true;
  }
  if (voiceNodeTuningStatus) {
    voiceNodeTuningStatus.textContent = "Saving tuning config...";
  }

  try {
    const payload = {
      enabled: Boolean(voiceNodeTuningEnabled?.checked),
      record_seconds: Number(voiceNodeTuningRecordSeconds?.value || 4),
      mic_record_gain: Number(voiceNodeTuningGain?.value || 32),
      vad_enabled: Boolean(voiceNodeTuningVadEnabled?.checked),
      vad_threshold: Number(voiceNodeTuningVadThreshold?.value || 40),
      vad_silence_stop_ms: Number(voiceNodeTuningVadSilence?.value || 900),
    };
    await updateVoiceNodeConfig(payload);
    if (voiceNodeTuningStatus) {
      voiceNodeTuningStatus.textContent = "Saved. Board will refresh config within about 10 seconds.";
    }
    await refreshVoiceNodePanel();
  } catch (error) {
    if (voiceNodeTuningStatus) {
      voiceNodeTuningStatus.textContent = getReadableErrorMessage(error, "Save tuning config failed");
    }
  } finally {
    if (submitButton) {
      submitButton.disabled = false;
    }
  }
});
deviceRegistryRefreshButton.addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  void refreshDeviceRegistry(true);
});
deviceRegistryList.addEventListener("submit", handleDeviceRegistrySubmit);
deviceCreateForm.addEventListener("submit", handleDeviceCreateSubmit);
deviceCreateType.addEventListener("change", updateDeviceCreateMode);
llmWarmupButton.addEventListener("click", warmupLlm);
llmSleepButton.addEventListener("click", sleepLlm);
refreshAllButton.addEventListener("click", async () => {
  await refreshDashboardStatus();
  await refreshDeviceRegistry(true);
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
updateDeviceCreateMode();
setVoiceLifecycleState(VOICE_STATE_STOPPED);
setKeepMicIndicator(false, "Push-to-Talk Mode พร้อมแล้ว");
setPillState(chatStatus, "neutral", "พร้อมใช้งาน");
setChatBusy(false);
refreshDashboardStatus();
refreshDeviceRegistry(true);
refreshVoiceDebugStatus();
refreshVoiceNodePanel();
window.setTimeout(() => void maybeStartVoiceNodeWakeOnLoad(), 1200);
window.setInterval(refreshDashboardStatus, 15000);
window.setInterval(refreshDeviceRegistry, 15000);
window.setInterval(refreshVoiceDebugStatus, 5000);
window.setInterval(refreshVoiceNodePanel, 3000);
