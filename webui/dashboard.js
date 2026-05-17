// ── Top-bar element refs ──
const tbTemperature = document.getElementById("tb-temperature");
const tbHumidity = document.getElementById("tb-humidity");
const esp32Dot = document.getElementById("esp32-dot");
const esp32StatusLabel = document.getElementById("esp32-status-label");
const relayDot = document.getElementById("relay-dot");
const relayStateLabel = document.getElementById("relay-state-label");

// ── Relay visual refs ──
const relayStateBadge = document.getElementById("relay-state-badge");
const relayGlow = document.getElementById("relay-glow");
const relayStateText = document.getElementById("relay-state-text");

// ── Motion dot ref ──
const motionDot = document.getElementById("motion-dot");

// ── Sensor temperature card ref ──
const sensorTempCard = document.getElementById("sensor-temp-card");

function updateRelayVisual(state) {
  if (!relayStateBadge) return;
  const STATE_MAP = {
    on:      { cls: "state-on",      text: "🟢 เปิดอยู่",    dot: "on",      chip: "เปิดอยู่" },
    off:     { cls: "state-off",     text: "⚫ ปิดอยู่",    dot: "off",     chip: "ปิดอยู่" },
    pending: { cls: "state-pending", text: "🟡 กำลังรอ",   dot: "pending", chip: "กำลังรอ" },
  };
  const s = STATE_MAP[state] || { cls: "state-off", text: "-- ไม่ทราบ", dot: "off", chip: "ไม่ทราบ" };
  relayStateBadge.className = `relay-state-badge ${s.cls}`;
  if (relayStateText) relayStateText.textContent = s.text;
  if (relayDot) relayDot.className = `relay-dot ${s.dot}`;
  if (relayStateLabel) relayStateLabel.textContent = s.chip;
  const relayDotAcc = document.getElementById("relay-dot-acc");
  const relayLabelAcc = document.getElementById("relay-label-acc");
  if (relayDotAcc) relayDotAcc.className = `relay-dot ${s.dot}`;
  if (relayLabelAcc) relayLabelAcc.textContent = s.chip;
}

function updateSensorTemperatureColor(temp) {
  if (!sensorTempCard) return;
  sensorTempCard.classList.remove("temp-hot", "temp-warm", "temp-cool");
  if (temp === null || temp === undefined) return;
  if (temp >= 35) sensorTempCard.classList.add("temp-hot");
  else if (temp >= 28) sensorTempCard.classList.add("temp-warm");
  else sensorTempCard.classList.add("temp-cool");
}

function updateMotionDot(detected) {
  if (!motionDot) return;
  motionDot.className = `motion-dot ${detected ? "detected" : ""}`;
}

function updateEsp32Dot(online) {
  if (!esp32Dot) return;
  esp32Dot.className = `status-dot ${online ? "online" : "offline"}`;
  if (esp32StatusLabel) esp32StatusLabel.textContent = online ? "ESP32 online" : "ESP32 offline";
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

async function refreshVoiceNodePanel() {
  if (!voiceNodeIndicator) {
    return;
  }

  if (voiceNodeRefreshButton) {
    voiceNodeRefreshButton.disabled = true;
  }
  if (voiceNodeRefreshStatus) {
    voiceNodeRefreshStatus.textContent = "กำลังอ่าน...";
  }

  try {
    const [nodeStatus, nodeConfig, audioStatus, streamStatus, audioHistory, audioReport] = await Promise.all([
      fetchVoiceNodeStatus(),
      fetchVoiceNodeConfig(),
      fetchVoiceNodeAudioStatus(),
      fetchVoiceNodeStreamStatus(),
      fetchVoiceNodeAudioHistory(),
      fetchVoiceNodeAudioReport(),
    ]);
    renderVoiceNodeTuning(nodeConfig);
    renderVoiceNodeReport(audioReport);

    setPillState(
      voiceNodeIndicator,
      nodeStatus.online ? "good" : "warn",
      nodeStatus.online ? "Voice node online" : "Voice node offline"
    );
    voiceNodeBoardStatus.textContent = nodeStatus.online
      ? `ออนไลน์ ${formatHeartbeatStatus(nodeStatus.last_seen_at, nodeStatus.seconds_since_heartbeat)}`
      : "ยังไม่ออนไลน์";
    voiceNodeState.textContent = [
      nodeStatus.ip_address || "-",
      nodeStatus.state || "-",
      nodeStatus.wake_mode_enabled
        ? (nodeStatus.wake_conversation_active ? "Wake: active" : "Wake: waiting")
        : "Wake: off",
      `คิวคำสั่ง ${nodeStatus.pending_command_count || 0}`,
    ].join(" | ");
    renderVoiceNodeStreamStatus(streamStatus);

    if (!audioStatus.has_result) {
      voiceNodeAudioTime.textContent = "ยังไม่มีการอัปโหลดเสียง";
      voiceNodeAudioSize.textContent = "-";
      if (voiceNodeAudioPlayer) {
        voiceNodeAudioPlayer.removeAttribute("src");
        voiceNodeAudioPlayer.load();
      }
      voiceNodeSttStatus.textContent = "-";
      if (voiceNodeSttRaw) {
        voiceNodeSttRaw.textContent = "-";
      }
      if (voiceNodePlaybackStatus) {
        voiceNodePlaybackStatus.textContent = audioStatus.playback_stage
          ? `${audioStatus.playback_stage}: ${audioStatus.playback_ok ? "สำเร็จ" : "ยังไม่สำเร็จ"}`
          : "-";
      }
      if (voiceNodePlaybackSize) {
        voiceNodePlaybackSize.textContent = audioStatus.playback_audio_size_bytes
          ? `${audioStatus.playback_audio_size_bytes} bytes`
          : "-";
      }
      voiceNodeHeardText.textContent = "-";
      voiceNodeReply.textContent = "-";
      if (voiceNodeExpectedDisplay) voiceNodeExpectedDisplay.textContent = "-";
      if (voiceNodeScore) voiceNodeScore.textContent = "-";
      renderVoiceNodeHistory(audioHistory.items || []);
      if (voiceNodeRefreshStatus) {
        voiceNodeRefreshStatus.textContent = "พร้อมรับคำสั่งทดสอบจากหน้าเว็บ";
      }
      return;
    }

    if (state.voiceNodeRecordPendingSince && audioStatus.received_at) {
      const receivedAtMs = new Date(audioStatus.received_at).getTime();
      if (Number.isFinite(receivedAtMs) && receivedAtMs >= state.voiceNodeRecordPendingSince - 1000) {
        state.voiceNodeRecordPendingSince = 0;
        if (voiceNodeRecordOnceButton) {
          voiceNodeRecordOnceButton.disabled = false;
        }
      }
    }

    voiceNodeAudioTime.textContent = formatHeartbeatStatus(
      audioStatus.received_at,
      audioStatus.seconds_since_received
    );
    if (audioStatus.uploaded_audio_size_bytes) {
      const audioParts = [
        `${audioStatus.uploaded_audio_size_bytes} bytes`,
        audioStatus.uploaded_audio_content_type || "audio",
      ];
      if (audioStatus.uploaded_audio_duration_ms) {
        audioParts.push(`${(audioStatus.uploaded_audio_duration_ms / 1000).toFixed(1)}s`);
      }
      if (audioStatus.uploaded_audio_quality) {
        audioParts.push(`quality: ${audioStatus.uploaded_audio_quality}`);
      }
      if (audioStatus.uploaded_audio_peak_ratio !== null && audioStatus.uploaded_audio_peak_ratio !== undefined) {
        audioParts.push(`peak: ${formatRatioPercent(audioStatus.uploaded_audio_peak_ratio)}`);
      }
      if (audioStatus.uploaded_audio_rms_ratio !== null && audioStatus.uploaded_audio_rms_ratio !== undefined) {
        audioParts.push(`rms: ${formatRatioPercent(audioStatus.uploaded_audio_rms_ratio)}`);
      }
      voiceNodeAudioSize.textContent = audioParts.join(" | ");
    } else {
      voiceNodeAudioSize.textContent = "-";
    }
    if (voiceNodeAudioPlayer && audioStatus.uploaded_audio_url) {
      const version = audioStatus.received_at ? new Date(audioStatus.received_at).getTime() : Date.now();
      const nextSrc = `${audioStatus.uploaded_audio_url}&v=${version}`;
      if (voiceNodeAudioPlayer.getAttribute("src") !== nextSrc) {
        voiceNodeAudioPlayer.src = nextSrc;
        voiceNodeAudioPlayer.load();
      }
    }
    voiceNodeSttStatus.textContent = audioStatus.stt_ok
      ? "อ่านเสียงสำเร็จ"
      : `ยังอ่านไม่เจอเสียงพูด${audioStatus.stt_error ? `: ${audioStatus.stt_error}` : ""}`;
    if (voiceNodeSttRaw) {
      const rawText = audioStatus.stt_raw_text || "";
      voiceNodeSttRaw.textContent =
        rawText && rawText !== audioStatus.heard_text ? rawText : "-";
    }
    if (voiceNodePlaybackStatus) {
      const playbackLabel = audioStatus.playback_stage || "-";
      const playbackResult = audioStatus.playback_ok === true
        ? "สำเร็จ"
        : audioStatus.playback_ok === false
          ? `ล้มเหลว${audioStatus.playback_error ? `: ${audioStatus.playback_error}` : ""}`
          : "รอรายงาน";
      voiceNodePlaybackStatus.textContent = `${playbackLabel} | ${playbackResult}`;
    }
    if (voiceNodePlaybackSize) {
      voiceNodePlaybackSize.textContent = audioStatus.playback_audio_size_bytes
        ? `${audioStatus.playback_audio_size_bytes} bytes`
        : "-";
    }
    voiceNodeHeardText.textContent = audioStatus.heard_text || "(ว่าง)";
    voiceNodeReply.textContent = audioStatus.reply || "-";
    if (voiceNodeExpectedDisplay) {
      voiceNodeExpectedDisplay.textContent = audioStatus.expected_text || "-";
    }
    if (voiceNodeScore) {
      voiceNodeScore.textContent = formatSttScore(audioStatus.stt_similarity);
    }
    renderVoiceNodeHistory(audioHistory.items || []);

    if (voiceNodeRefreshStatus) {
      voiceNodeRefreshStatus.textContent = audioStatus.stt_ok
        ? "ได้ข้อความจากบอร์ดแล้ว"
        : "อัปโหลดผ่าน แต่ STT ยังไม่ได้ข้อความ";
    }
  } catch (error) {
    setPillState(voiceNodeIndicator, "bad", "อ่านไม่ได้");
    voiceNodeBoardStatus.textContent = "อ่านสถานะไม่สำเร็จ";
    voiceNodeState.textContent = "-";
    voiceNodeAudioTime.textContent = "-";
    voiceNodeAudioSize.textContent = "-";
    renderVoiceNodeStreamStatus(null);
    voiceNodeSttStatus.textContent = getReadableErrorMessage(error, "โหลดไม่สำเร็จ");
    if (voiceNodeSttRaw) {
      voiceNodeSttRaw.textContent = "-";
    }
    if (voiceNodePlaybackStatus) {
      voiceNodePlaybackStatus.textContent = "-";
    }
    if (voiceNodePlaybackSize) {
      voiceNodePlaybackSize.textContent = "-";
    }
    voiceNodeHeardText.textContent = "-";
    voiceNodeReply.textContent = "-";
    if (voiceNodeExpectedDisplay) voiceNodeExpectedDisplay.textContent = "-";
    if (voiceNodeScore) voiceNodeScore.textContent = "-";
    renderVoiceNodeHistory([]);
    renderVoiceNodeReport(null);
    if (voiceNodeRefreshStatus) {
      voiceNodeRefreshStatus.textContent = "ลองรีเฟรชอีกครั้ง";
    }
  } finally {
    if (voiceNodeRefreshButton) {
      voiceNodeRefreshButton.disabled = false;
    }
  }
}

function renderVoiceNodeReport(report) {
  if (!voiceNodeReportStatus || !voiceNodeReportSummary) {
    return;
  }
  if (!report) {
    setPillState(voiceNodeReportStatus, "neutral", "ยังไม่มีรายงาน");
    voiceNodeReportSummary.textContent = "ยังไม่มีข้อมูลทดสอบ";
    return;
  }

  if (report.ready_for_demo) {
    setPillState(voiceNodeReportStatus, "good", "พร้อมเดโม");
  } else if (report.total_items >= 5) {
    setPillState(voiceNodeReportStatus, "warn", "ต้องจูนเพิ่ม");
  } else {
    setPillState(voiceNodeReportStatus, "neutral", "กำลังเก็บข้อมูล");
  }

  const parts = [
    `Audio OK: ${Math.round((report.audio_quality_ok_rate || 0) * 100)}%`,
    `รอบ: ${report.total_items}`,
    `STT: ${Math.round((report.stt_success_rate || 0) * 100)}%`,
    `Score: ${formatSttScore(report.average_similarity)}`,
    `Playback: ${Math.round((report.playback_success_rate || 0) * 100)}%`,
  ];
  if (report.average_peak_ratio !== null && report.average_peak_ratio !== undefined) {
    parts.push(`Peak: ${formatRatioPercent(report.average_peak_ratio)}`);
  }
  if (report.average_rms_ratio !== null && report.average_rms_ratio !== undefined) {
    parts.push(`RMS: ${formatRatioPercent(report.average_rms_ratio)}`);
  }
  if (report.low_score_count) {
    parts.push(`low score: ${report.low_score_count}`);
  }
  if (report.quiet_warning_count) {
    parts.push(`quiet: ${report.quiet_warning_count}`);
  }
  if (report.clipping_warning_count) {
    parts.push(`clipped: ${report.clipping_warning_count}`);
  }
  if (report.average_uploaded_duration_ms) {
    parts.push(`เสียงเฉลี่ย: ${(report.average_uploaded_duration_ms / 1000).toFixed(1)}s`);
  }
  voiceNodeReportSummary.textContent = `${parts.join(" | ")} — ${(report.notes || []).join(" / ")}`;
}

function renderVoiceNodeStreamStatus(streamStatus) {
  if (!voiceNodeStreamStatus || !voiceNodeStreamStats) {
    return;
  }

  if (!streamStatus) {
    voiceNodeStreamStatus.textContent = "-";
    voiceNodeStreamStats.textContent = "-";
    return;
  }

  voiceNodeStreamStatus.textContent = streamStatus.connected
    ? "connected"
    : streamStatus.last_frame_at
      ? `idle ${formatHeartbeatStatus(streamStatus.last_frame_at, streamStatus.seconds_since_last_frame)}`
      : "not connected";

  const parts = [
    `${streamStatus.frame_count || 0} frames`,
    `${streamStatus.total_bytes || 0} bytes`,
    `${Number(streamStatus.estimated_audio_seconds || 0).toFixed(1)}s`,
  ];
  if (streamStatus.last_peak_ratio !== null && streamStatus.last_peak_ratio !== undefined) {
    parts.push(`peak ${formatRatioPercent(streamStatus.last_peak_ratio)}`);
  }
  if (streamStatus.last_rms_ratio !== null && streamStatus.last_rms_ratio !== undefined) {
    parts.push(`rms ${formatRatioPercent(streamStatus.last_rms_ratio)}`);
  }
  parts.push(streamStatus.speech_active ? "speech" : "silence");
  if (streamStatus.utterance_count) {
    parts.push(`${streamStatus.utterance_count} utterance`);
  }
  if (streamStatus.speech_audio_seconds) {
    parts.push(`speech ${Number(streamStatus.speech_audio_seconds).toFixed(1)}s`);
  }
  if (streamStatus.vad_start_frames && streamStatus.vad_end_frames) {
    parts.push(`vad ${streamStatus.vad_start_frames}/${streamStatus.vad_end_frames}`);
  }
  if (streamStatus.last_error) {
    parts.push(`error ${streamStatus.last_error}`);
  }
  voiceNodeStreamStats.textContent = parts.join(" | ");
}

function renderVoiceNodeTuning(config) {
  if (!config || !voiceNodeTuningForm) {
    return;
  }
  if (document.activeElement && voiceNodeTuningForm.contains(document.activeElement)) {
    return;
  }
  if (voiceNodeTuningEnabled) {
    voiceNodeTuningEnabled.checked = Boolean(config.enabled);
  }
  if (voiceNodeTuningRecordSeconds) {
    voiceNodeTuningRecordSeconds.value = String(config.record_seconds ?? 4);
  }
  if (voiceNodeTuningGain) {
    voiceNodeTuningGain.value = String(config.mic_record_gain ?? 24);
  }
  if (voiceNodeTuningVadEnabled) {
    voiceNodeTuningVadEnabled.checked = Boolean(config.vad_enabled);
  }
  if (voiceNodeTuningVadThreshold) {
    voiceNodeTuningVadThreshold.value = String(config.vad_threshold ?? 40);
  }
  if (voiceNodeTuningVadSilence) {
    voiceNodeTuningVadSilence.value = String(config.vad_silence_stop_ms ?? 900);
  }
}

function renderVoiceNodeHistory(items) {
  if (!voiceNodeHistoryList) {
    return;
  }
  if (!items.length) {
    voiceNodeHistoryList.replaceChildren(
      createRegistryText("p", "debug-line", "ยังไม่มีประวัติการทดสอบเสียงจากบอร์ด")
    );
    return;
  }

  const fragment = document.createDocumentFragment();
  for (const item of items.slice(0, 10)) {
    const card = document.createElement("article");
    card.className = `voice-node-history-item ${item.stt_ok ? "ok" : "warn"}`;

    const header = document.createElement("div");
    header.className = "voice-node-history-header";
    header.appendChild(
      createRegistryText(
        "strong",
        "",
        item.stt_ok ? "STT สำเร็จ" : "STT ยังไม่เจอเสียงพูด"
      )
    );
    header.appendChild(
      createRegistryText(
        "span",
        "debug-line",
        formatHeartbeatStatus(item.received_at, item.seconds_since_received)
      )
    );
    card.appendChild(header);

    const meta = document.createElement("div");
    meta.className = "message-meta";
    meta.appendChild(createRegistryText("span", "badge", `intent: ${item.intent || "-"}`));
    meta.appendChild(createRegistryText("span", "badge", `source: ${item.source || "-"}`));
    meta.appendChild(
      createRegistryText(
        "span",
        "badge",
        `playback: ${formatVoiceNodePlayback(item)}`
      )
    );
    if (item.stt_similarity !== null && item.stt_similarity !== undefined) {
      meta.appendChild(createRegistryText("span", "badge", `score: ${formatSttScore(item.stt_similarity)}`));
    }
    if (item.uploaded_audio_duration_ms) {
      meta.appendChild(
        createRegistryText(
          "span",
          "badge",
          `audio: ${(item.uploaded_audio_duration_ms / 1000).toFixed(1)}s`
        )
      );
    }
    if (item.uploaded_audio_quality) {
      meta.appendChild(createRegistryText("span", "badge", `quality: ${item.uploaded_audio_quality}`));
    }
    if (item.uploaded_audio_peak_ratio !== null && item.uploaded_audio_peak_ratio !== undefined) {
      meta.appendChild(createRegistryText("span", "badge", `peak: ${formatRatioPercent(item.uploaded_audio_peak_ratio)}`));
    }
    if (item.uploaded_audio_rms_ratio !== null && item.uploaded_audio_rms_ratio !== undefined) {
      meta.appendChild(createRegistryText("span", "badge", `rms: ${formatRatioPercent(item.uploaded_audio_rms_ratio)}`));
    }
    card.appendChild(meta);

    if (item.expected_text) {
      card.appendChild(
        createRegistryText("p", "debug-line", `ควรพูด: ${item.expected_text}`)
      );
    }
    card.appendChild(
      createRegistryText(
        "p",
        "voice-node-history-text",
        `ได้ยินว่า: ${item.heard_text || "(ว่าง)"}`
      )
    );
    if (item.stt_raw_text && item.stt_raw_text !== item.heard_text) {
      card.appendChild(
        createRegistryText("p", "debug-line", `STT ดิบ: ${item.stt_raw_text}`)
      );
    }
    if (!item.stt_ok && item.stt_error) {
      card.appendChild(
        createRegistryText("p", "debug-line", `error: ${item.stt_error}`)
      );
    }
    if (Array.isArray(item.uploaded_audio_quality_notes) && item.uploaded_audio_quality_notes.length) {
      card.appendChild(
        createRegistryText("p", "debug-line", `audio note: ${item.uploaded_audio_quality_notes.join(" / ")}`)
      );
    }
    card.appendChild(
      createRegistryText(
        "p",
        "voice-node-history-reply",
        `AI: ${item.reply || "-"}`
      )
    );

    fragment.appendChild(card);
  }
  voiceNodeHistoryList.replaceChildren(fragment);
}

function formatVoiceNodePlayback(item) {
  if (item.playback_ok === true) {
    return `${item.playback_stage || "ok"} ok`;
  }
  if (item.playback_ok === false) {
    return `${item.playback_stage || "failed"} failed`;
  }
  return "รอรายงาน";
}

function formatSttScore(score) {
  if (score === null || score === undefined) {
    return "-";
  }
  return `${Math.round(Number(score) * 100)}%`;
}

function formatRatioPercent(value) {
  return `${Math.round(Number(value) * 100)}%`;
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

async function refreshDeviceRegistry(force = false) {
  if (!deviceRegistryList || !deviceRegistryIndicator) {
    return;
  }
  if (!force && isDeviceRegistryEditing()) {
    setPillState(deviceRegistryIndicator, "neutral", "กำลังแก้ไข");
    return;
  }

  if (deviceRegistryRefreshButton) {
    deviceRegistryRefreshButton.disabled = true;
  }
  setPillState(deviceRegistryIndicator, "neutral", "กำลังโหลด");

  try {
    const data = await fetchDeviceRegistryStatus();
    renderDeviceRegistry(data.devices || []);
    setPillState(
      deviceRegistryIndicator,
      data.total > 0 ? "good" : "warn",
      `${data.enabled || 0}/${data.total || 0} enabled`
    );
    // Update relay state badge from relay_1 device state
    const relayDevice = (data.devices || []).find(
      (d) => d.device_type === "relay" && d.enabled
    );
    if (relayDevice) {
      updateRelayVisual(relayDevice.state || "unknown");
    }
  } catch (error) {
    deviceRegistryList.replaceChildren(
      createRegistryText("p", "debug-line", "อ่าน Device Registry ไม่สำเร็จ ลอง restart server แล้วรีเฟรชอีกครั้ง")
    );
    setPillState(deviceRegistryIndicator, "bad", "โหลดไม่ได้");
  } finally {
    if (deviceRegistryRefreshButton) {
      deviceRegistryRefreshButton.disabled = false;
    }
  }
}

function isDeviceRegistryEditing() {
  const activeElement = document.activeElement;
  return Boolean(activeElement?.closest?.(".device-registry-form, .device-create-form"));
}

function updateDeviceCreateMode() {
  if (!deviceCreateForm || !deviceCreateType) {
    return;
  }
  const deviceType = deviceCreateType.value || "virtual";
  deviceCreateForm.dataset.deviceType = deviceType;
  if (deviceCreateSubmit) {
    deviceCreateSubmit.textContent =
      deviceType === "relay" ? "เพิ่ม relay พร้อมตรวจ GPIO" : "เพิ่ม virtual device";
  }
}

function renderDeviceRegistry(devices) {
  if (!devices.length) {
    deviceRegistryList.replaceChildren(
      createRegistryText("p", "debug-text", "ยังไม่มีอุปกรณ์ใน Device Registry")
    );
    return;
  }

  const fragment = document.createDocumentFragment();
  for (const device of devices) {
    fragment.appendChild(createDeviceRegistryItem(device));
  }
  deviceRegistryList.replaceChildren(fragment);
}

function createDeviceRegistryItem(device) {
  const item = document.createElement("article");
  item.className = "device-registry-item";

  const main = document.createElement("div");
  main.className = "device-registry-main";

  const titleBlock = document.createElement("div");
  titleBlock.appendChild(
    createRegistryText("p", "device-registry-name", device.display_name || device.id || "-")
  );
  titleBlock.appendChild(
    createRegistryText(
      "p",
      "device-registry-meta",
      [
        `id: ${device.id || "-"}`,
        `type: ${device.device_type || "-"}`,
        `room: ${device.room || "-"}`,
      ].join(" | ")
    )
  );

  main.appendChild(titleBlock);
  main.appendChild(
    createRegistryText(
      "span",
      `status-pill ${getDeviceStateClass(device.state)}`,
      getDeviceStateLabel(device.state)
    )
  );
  item.appendChild(main);

  const detail = document.createElement("dl");
  detail.className = "detail-list";
  appendRegistryDetail(detail, "ESP32", device.esp32_device_id || "-");
  appendRegistryDetail(detail, "GPIO", device.gpio_pin === null || device.gpio_pin === undefined ? "-" : String(device.gpio_pin));
  appendRegistryDetail(detail, "Pin mode", device.pin_mode || "-");
  appendRegistryDetail(detail, "Relay channel", device.relay_channel || "-");
  appendRegistryDetail(detail, "Active high", device.active_high === null || device.active_high === undefined ? "-" : String(Boolean(device.active_high)));
  appendRegistryDetail(detail, "Command", device.last_command_status || "-");
  appendRegistryDetail(detail, "Updated", formatDate(device.last_updated_at));
  item.appendChild(detail);

  const aliasWrap = document.createElement("div");
  aliasWrap.className = "device-registry-aliases";
  for (const alias of device.aliases || []) {
    aliasWrap.appendChild(createRegistryText("span", "badge", alias));
  }
  if (!aliasWrap.children.length) {
    aliasWrap.appendChild(createRegistryText("span", "badge", "no alias"));
  }
  item.appendChild(aliasWrap);
  item.appendChild(createDeviceRegistryForm(device));

  return item;
}

function createDeviceRegistryForm(device) {
  const form = document.createElement("form");
  form.className = "device-registry-form";
  form.dataset.deviceId = device.id || "";

  form.appendChild(
    createLabeledInput(
      "ชื่อ",
      "display_name",
      device.display_name || "",
      "เช่น ไฟโต๊ะ"
    )
  );
  form.appendChild(
    createLabeledInput(
      "ห้อง",
      "room",
      device.room || "",
      "เช่น ห้องนั่งเล่น"
    )
  );
  form.appendChild(
    createLabeledTextarea(
      "คำเรียก",
      "aliases",
      (device.aliases || []).join(", "),
      "คั่นด้วย comma เช่น ไฟโต๊ะ, หลอดไฟ, ไฟ"
    )
  );

  const enabledLabel = document.createElement("label");
  enabledLabel.className = "device-registry-enabled";
  const enabledInput = document.createElement("input");
  enabledInput.type = "checkbox";
  enabledInput.name = "enabled";
  enabledInput.checked = Boolean(device.enabled);
  enabledLabel.appendChild(enabledInput);
  enabledLabel.appendChild(document.createTextNode(" เปิดใช้งานอุปกรณ์นี้"));
  form.appendChild(enabledLabel);

  const actions = document.createElement("div");
  actions.className = "device-registry-form-actions";
  const saveButton = document.createElement("button");
  saveButton.type = "submit";
  saveButton.textContent = "บันทึกชื่อ/alias";
  actions.appendChild(saveButton);
  actions.appendChild(createRegistryText("span", "loading-text device-registry-save-status", ""));
  form.appendChild(actions);

  return form;
}

function createLabeledInput(labelText, name, value, placeholder) {
  const label = document.createElement("label");
  label.className = "device-registry-field";
  label.appendChild(createRegistryText("span", "", labelText));
  const input = document.createElement("input");
  input.name = name;
  input.type = "text";
  input.value = value;
  input.placeholder = placeholder;
  input.required = name === "display_name";
  label.appendChild(input);
  return label;
}

function createLabeledTextarea(labelText, name, value, placeholder) {
  const label = document.createElement("label");
  label.className = "device-registry-field device-registry-field-wide";
  label.appendChild(createRegistryText("span", "", labelText));
  const textarea = document.createElement("textarea");
  textarea.name = name;
  textarea.rows = 2;
  textarea.value = value;
  textarea.placeholder = placeholder;
  label.appendChild(textarea);
  return label;
}

async function handleDeviceRegistrySubmit(event) {
  const form = event.target.closest("form.device-registry-form");
  if (!form) {
    return;
  }
  event.preventDefault();

  const deviceId = form.dataset.deviceId;
  if (!deviceId) {
    return;
  }

  const saveButton = form.querySelector("button[type='submit']");
  const statusElement = form.querySelector(".device-registry-save-status");
  if (saveButton) {
    saveButton.disabled = true;
  }
  if (statusElement) {
    statusElement.textContent = "กำลังบันทึก...";
  }

  try {
    const formData = new FormData(form);
    await updateDeviceMetadata(deviceId, {
      display_name: String(formData.get("display_name") || "").trim(),
      room: String(formData.get("room") || "").trim(),
      aliases: parseAliasInput(String(formData.get("aliases") || "")),
      enabled: formData.get("enabled") === "on",
    });
    if (statusElement) {
      statusElement.textContent = "บันทึกแล้ว";
    }
    await refreshDeviceRegistry(true);
  } catch (error) {
    if (statusElement) {
      statusElement.textContent = getReadableErrorMessage(error, "บันทึกไม่สำเร็จ");
    }
  } finally {
    if (saveButton) {
      saveButton.disabled = false;
    }
  }
}

async function handleDeviceCreateSubmit(event) {
  event.preventDefault();
  if (!deviceCreateForm) {
    return;
  }

  if (deviceCreateSubmit) {
    deviceCreateSubmit.disabled = true;
  }
  if (deviceCreateStatus) {
    deviceCreateStatus.textContent = "กำลังเพิ่มอุปกรณ์...";
  }

  try {
    const formData = new FormData(deviceCreateForm);
    const displayName = String(formData.get("display_name") || "").trim();
    const deviceType = String(formData.get("device_type") || "virtual");
    const payload = {
      display_name: displayName,
      device_type: deviceType,
      room: String(formData.get("room") || "").trim(),
      aliases: parseAliasInput(String(formData.get("aliases") || displayName)),
      enabled: formData.get("enabled") === "on",
    };
    if (deviceType === "relay") {
      payload.esp32_device_id = optionalString(formData.get("esp32_device_id"));
      payload.gpio_pin = optionalInteger(formData.get("gpio_pin"));
      payload.relay_channel = optionalInteger(formData.get("relay_channel")) || 1;
      payload.active_high = formData.get("active_high") === "on";
    }

    await createDevice(payload);
    deviceCreateForm.reset();
    const enabledInput = deviceCreateForm.querySelector("input[name='enabled']");
    if (enabledInput) {
      enabledInput.checked = true;
    }
    const activeHighInput = deviceCreateForm.querySelector("input[name='active_high']");
    if (activeHighInput) {
      activeHighInput.checked = true;
    }
    const relayChannelInput = deviceCreateForm.querySelector("input[name='relay_channel']");
    if (relayChannelInput) {
      relayChannelInput.value = "1";
    }
    updateDeviceCreateMode();
    if (deviceCreateStatus) {
      deviceCreateStatus.textContent =
        deviceType === "relay" ? "เพิ่ม relay แล้ว" : "เพิ่ม virtual device แล้ว";
    }
    await refreshDeviceRegistry(true);
  } catch (error) {
    if (deviceCreateStatus) {
      deviceCreateStatus.textContent = getReadableErrorMessage(error, "เพิ่มอุปกรณ์ไม่สำเร็จ");
    }
  } finally {
    if (deviceCreateSubmit) {
      deviceCreateSubmit.disabled = false;
    }
  }
}

function optionalString(value) {
  const text = String(value || "").trim();
  return text || null;
}

function optionalInteger(value) {
  const text = String(value || "").trim();
  if (!text) {
    return null;
  }
  const parsedValue = Number(text);
  return Number.isInteger(parsedValue) ? parsedValue : null;
}

function parseAliasInput(value) {
  const seen = new Set();
  const aliases = [];
  for (const part of value.split(/[,，\n]/)) {
    const alias = part.trim();
    if (!alias) {
      continue;
    }
    const normalizedAlias = normalizeThaiText(alias);
    if (seen.has(normalizedAlias)) {
      continue;
    }
    seen.add(normalizedAlias);
    aliases.push(alias);
  }
  return aliases;
}

function appendRegistryDetail(parent, label, value) {
  const row = document.createElement("div");
  row.appendChild(createRegistryText("dt", "", label));
  row.appendChild(createRegistryText("dd", "", value));
  parent.appendChild(row);
}

function createRegistryText(tagName, className, text) {
  const element = document.createElement(tagName);
  if (className) {
    element.className = className;
  }
  element.textContent = text;
  return element;
}

function getDeviceStateClass(state) {
  if (state === "on") {
    return "good";
  }
  if (state === "pending") {
    return "warn";
  }
  if (state === "unavailable") {
    return "bad";
  }
  return "neutral";
}

function getDeviceStateLabel(state) {
  if (state === "on") {
    return "ON";
  }
  if (state === "off") {
    return "OFF";
  }
  if (state === "pending") {
    return "PENDING";
  }
  if (state === "unavailable") {
    return "UNAVAILABLE";
  }
  return "UNKNOWN";
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
      // Keep aggregate state if the direct ESP32 status endpoint is temporarily unavailable.
    }

    state.maxChatHistoryItems =
      Number.isFinite(data.app?.max_chat_history_items) && data.app.max_chat_history_items > 0
        ? data.app.max_chat_history_items
        : state.maxChatHistoryItems;
    trimChatHistory();
    updateLlmStatus(data.llm);

    // Sensor panel
    const tempVal = data.sensor.temperature;
    const humVal = data.sensor.humidity;
    sensorDeviceId.textContent = data.sensor.device_id || "-";
    sensorTemperature.textContent = tempVal === null || tempVal === undefined ? "-" : `${Math.round(tempVal)} °C`;
    sensorHumidity.textContent = humVal === null || humVal === undefined ? "-" : `${Math.round(humVal)} %`;
    sensorFreshness.textContent = data.sensor.is_fresh ? "ข้อมูลล่าสุดพร้อมใช้งาน" : "ยังไม่มีข้อมูลใหม่";
    sensorUpdated.textContent = formatDate(data.sensor.received_at || data.sensor.timestamp);
    updateSensorTemperatureColor(tempVal);

    // Top bar sensor
    if (tbTemperature) tbTemperature.textContent = tempVal !== null && tempVal !== undefined ? `${Math.round(tempVal)} °C` : "--";
    if (tbHumidity) tbHumidity.textContent = humVal !== null && humVal !== undefined ? `${Math.round(humVal)} %` : "--";

    // Motion panel
    const motionDetected = Boolean(data.motion.motion_detected);
    motionStatus.textContent = motionDetected ? "พบการเคลื่อนไหว" : "ยังไม่พบการเคลื่อนไหว";
    motionLastDetected.textContent = formatDate(data.motion.last_motion_at);
    motionLastEvent.textContent = formatDate(data.motion.last_event_at);
    motionGreeting.textContent = data.motion.greeting_message || "-";
    updateMotionDot(motionDetected);

    if (!state.pirTouched) {
      pirSimToggle.checked = motionDetected;
    }

    // ESP32 / Device Control panel
    updateEsp32Dot(esp32Status.online);
    setPillState(
      deviceOnlineIndicator,
      esp32Status.online ? "good" : "warn",
      esp32Status.online ? "ESP32 online" : "ESP32 offline"
    );
    deviceLatestCommand.textContent = esp32Status.latest_command
      ? `relay ch${esp32Status.latest_command.channel} → ${esp32Status.latest_command.action}`
      : "-";
    devicePendingCount.textContent = String(esp32Status.pending_command_count ?? 0);
    deviceLastSeen.textContent = formatHeartbeatStatus(
      esp32Status.last_seen_at,
      esp32Status.seconds_since_heartbeat
    );
    renderEsp32Capabilities(esp32Status.capabilities || null);

    // Voice panel
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
    renderEsp32Capabilities(null);
    setPillState(deviceOnlineIndicator, "bad", "อ่านสถานะไม่ได้");
    setPillState(voiceModeIndicator, "bad", "อ่านสถานะไม่ได้");
  }
}

function renderEsp32Capabilities(capabilities) {
  if (!esp32CapabilitiesBox) {
    return;
  }
  if (!capabilities) {
    esp32CapabilitiesBox.replaceChildren(
      createRegistryText("p", "debug-text", "ยังไม่มีข้อมูล capabilities จาก ESP32")
    );
    return;
  }

  const wrapper = document.createElement("div");
  wrapper.className = "capabilities-card";
  wrapper.appendChild(
    createRegistryText(
      "p",
      "device-registry-name",
      `${capabilities.board_type || "ESP32"} ${capabilities.firmware_version || ""}`.trim()
    )
  );
  wrapper.appendChild(
    createRegistryText(
      "p",
      "device-registry-meta",
      `อัปเดตล่าสุด: ${formatDate(capabilities.received_at || capabilities.timestamp)}`
    )
  );

  const rows = document.createElement("dl");
  rows.className = "detail-list";
  appendRegistryDetail(rows, "Capabilities", formatList(capabilities.capabilities));
  appendRegistryDetail(rows, "Relay pins", formatList(capabilities.relay_pins));
  appendRegistryDetail(rows, "Sensor pins", formatList(capabilities.sensor_pins));
  appendRegistryDetail(rows, "I2S pins", formatList(capabilities.i2s_pins));
  appendRegistryDetail(rows, "Reserved pins", formatList(capabilities.reserved_pins));
  appendRegistryDetail(rows, "Available pins", formatList(capabilities.available_pins));
  wrapper.appendChild(rows);

  esp32CapabilitiesBox.replaceChildren(wrapper);
}

function formatList(values) {
  if (!Array.isArray(values) || !values.length) {
    return "-";
  }
  return values.join(", ");
}
