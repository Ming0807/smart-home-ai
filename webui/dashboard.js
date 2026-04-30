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
