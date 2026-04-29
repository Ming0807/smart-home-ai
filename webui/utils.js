function formatDate(value) {
  if (!value) {
    return "-";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString("th-TH", {
    dateStyle: "short",
    timeStyle: "medium",
  });
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function formatChatLatencyMs(latencyMs) {
  if (!Number.isFinite(latencyMs)) {
    return null;
  }
  if (latencyMs < 1000) {
    return `${Math.round(latencyMs)}ms`;
  }
  return `${(latencyMs / 1000).toFixed(1)}s`;
}

function parseSseBlock(block) {
  let event = "message";
  const dataLines = [];

  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }

  const dataText = dataLines.join("\n").trim();
  return {
    event,
    data: dataText ? JSON.parse(dataText) : {},
  };
}

function getAudioToken(url) {
  try {
    const resolvedUrl = new URL(url, window.location.origin);
    return resolvedUrl.searchParams.get("token");
  } catch (error) {
    return null;
  }
}

function normalizeThaiText(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/\s+/g, "");
}
