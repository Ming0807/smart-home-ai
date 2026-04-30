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
