async function fetchJson(url, options = {}, timeoutMs = 30000) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      cache: "no-store",
    });
    const text = await response.text();
    const data = text ? JSON.parse(text) : {};
    return { response, data };
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function fetchChatStream(message, handlers = {}, timeoutMs = 70000) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

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

async function fetchDeviceRegistryStatus() {
  const { response, data } = await fetchJson("/devices/status", {}, 10000);
  if (!response.ok) {
    throw new Error("device registry status failed");
  }
  return data;
}

function getApiErrorDetail(data, fallbackText) {
  if (typeof data?.detail === "string") {
    return data.detail;
  }
  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((item) => item?.msg || item?.message || "")
      .filter(Boolean)
      .join(" | ") || fallbackText;
  }
  if (typeof data?.error === "string") {
    return data.error;
  }
  return fallbackText;
}

async function updateDeviceMetadata(deviceId, payload) {
  const { response, data } = await fetchJson(
    `/devices/${encodeURIComponent(deviceId)}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    10000
  );
  if (!response.ok) {
    throw new Error(getApiErrorDetail(data, "device metadata update failed"));
  }
  return data.device;
}

async function createDevice(payload) {
  const { response, data } = await fetchJson(
    "/devices",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    10000
  );
  if (!response.ok) {
    throw new Error(getApiErrorDetail(data, "device create failed"));
  }
  return data.device;
}

async function createVirtualDevice(payload) {
  return createDevice({ ...payload, device_type: "virtual" });
}
