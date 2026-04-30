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
    const finalData = await fetchChatStream(
      message,
      {
        onStatus: (statusText) => {
          if (statusText) {
            setChatLoadingText(statusText);
          }
        },
        onChunk: (chunk) => {
          streamedText += chunk;
          updateAssistantEntryText(assistantEntry, streamedText);
        },
      },
      CHAT_REQUEST_TIMEOUT_MS
    );

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

async function sendChatMessage(message) {
  const trimmed = message.trim();
  if (!trimmed || state.chatBusy || state.recording) {
    return;
  }

  const apiMessage = buildChatApiMessage(trimmed, state.chatResponseMode);
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
