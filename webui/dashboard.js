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
  } catch (error) {
    deviceRegistryList.replaceChildren(
      createRegistryText("p", "debug-text", "อ่าน Device Registry ไม่สำเร็จ ลอง restart server แล้วรีเฟรชอีกครั้ง")
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
    renderEsp32Capabilities(esp32Status.capabilities || null);

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
