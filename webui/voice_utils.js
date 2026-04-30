const SpeechRecognitionConstructor =
  window.SpeechRecognition || window.webkitSpeechRecognition || null;

const WAKE_PHRASE_PATTERNS = [
  /น้อง\s*ฟ้า/iu,
  /น้อง\s*ฟ่า/iu,
  /น้อง\s*ฟา/iu,
  /นอง\s*ฟ้า/iu,
  /nong\s*fa/i,
];

const EXIT_WORDS = ["ขอบคุณ", "พอแล้ว", "เลิกคุย", "แค่นี้แหละ"];
const VOICE_STATE_STOPPED = "STOPPED";
const VOICE_STATE_IDLE_WAKE = "IDLE_LISTENING_WAKE_WORD";
const VOICE_STATE_ACTIVE = "ACTIVE_CONVERSATION";
const ACTIVE_LISTEN_RETRY_LIMIT = 2;
const ACTIVE_LISTEN_RETRY_DELAY_MS = 900;
const POST_SPEAKING_COOLDOWN_MS = 1800;
const WAKE_LISTEN_RESTART_DELAY_MS = 350;
const WAKE_LISTEN_WATCHDOG_MS = 15000;
const VOICE_RECORD_MIN_MS = 900;
const VOICE_RECORD_MAX_MS = 12000;
const VOICE_NO_SPEECH_TIMEOUT_MS = 6500;
const VOICE_SILENCE_STOP_MS = 1200;
const VOICE_SPEECH_RMS_THRESHOLD = 0.012;
const SPEECH_RECOGNITION_TURN_TIMEOUT_MS = 12000;
const SPEECH_RECOGNITION_LOOP_RESTART_MS = 500;
const ASSISTANT_ECHO_WINDOW_MS = 6000;
const DUPLICATE_TRANSCRIPT_WINDOW_MS = 2000;
const CHAT_REQUEST_TIMEOUT_MS = 70000;
const CHAT_WAITING_HINT_DELAY_MS = 6000;
const CHAT_LONG_WAIT_HINT_DELAY_MS = 18000;
const CHAT_MODE_FAST = "fast";
const CHAT_MODE_THINKING = "thinking";
const THINKING_TRIGGER_PREFIX = "คิดก่อนตอบ";
const THINKING_TRIGGER_PHRASES = [
  "คิดก่อนตอบ",
  "คิดก่อน",
  "วิเคราะห์ก่อน",
  "ขอคิดละเอียด",
  "คิดให้ละเอียด",
  "ขอวิเคราะห์",
  "deep think",
  "think carefully",
];
const REAL_THINKING_TRIGGER_PHRASES = [
  "คิดลึกจริง",
  "คิดแบบลึกจริง",
  "ใช้ thinking จริง",
  "เปิด thinking จริง",
  "real thinking",
  "deep think true",
];

function browserSupportsRecording() {
  return Boolean(window.MediaRecorder && navigator.mediaDevices?.getUserMedia);
}

function browserSupportsSpeechRecognition() {
  return Boolean(SpeechRecognitionConstructor);
}

function normalizeModeTriggerText(text) {
  return text.toLocaleLowerCase().replace(/\s+/g, "");
}

function messageHasThinkingTrigger(message) {
  const normalizedMessage = normalizeModeTriggerText(message);
  const triggerPhrases = [...THINKING_TRIGGER_PHRASES, ...REAL_THINKING_TRIGGER_PHRASES];
  return triggerPhrases.some((phrase) =>
    normalizedMessage.includes(normalizeModeTriggerText(phrase))
  );
}

function buildChatApiMessage(message, chatResponseMode) {
  if (chatResponseMode !== CHAT_MODE_THINKING || messageHasThinkingTrigger(message)) {
    return message;
  }
  return `${THINKING_TRIGGER_PREFIX} ${message}`;
}

function normalizeVoicePayload(payload) {
  if (payload && payload.data) {
    return payload.data;
  }
  return payload;
}

function isExitPhrase(text) {
  const normalized = normalizeThaiText(text);
  return EXIT_WORDS.some((word) => normalized.includes(normalizeThaiText(word)));
}

function detectWakePhrase(text) {
  for (const pattern of WAKE_PHRASE_PATTERNS) {
    const match = text.match(pattern);
    if (!match) {
      continue;
    }
    const remaining = text
      .replace(pattern, "")
      .replace(/^[\s,.!?-]+|[\s,.!?-]+$/g, "")
      .trim();
    return {
      matched: match[0],
      remaining,
    };
  }
  return null;
}

function collectSpeechResultText(event) {
  const finalParts = [];
  const interimParts = [];

  for (let index = event.resultIndex || 0; index < event.results.length; index += 1) {
    const result = event.results[index];
    const text = result[0]?.transcript || "";
    if (!text) {
      continue;
    }
    if (result.isFinal) {
      finalParts.push(text);
    } else {
      interimParts.push(text);
    }
  }

  return {
    finalText: finalParts.join(" ").trim(),
    interimText: interimParts.join(" ").trim(),
  };
}

function getSupportedRecordingMimeType() {
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4",
  ];

  for (const candidate of candidates) {
    if (window.MediaRecorder && MediaRecorder.isTypeSupported(candidate)) {
      return candidate;
    }
  }

  return "";
}

function getReadableErrorMessage(error, fallbackText) {
  if (error && error.name === "AbortError") {
    return "คำขอนี้ใช้เวลานานเกินไป ลองใหม่อีกครั้งได้";
  }
  if (error instanceof TypeError) {
    return "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ ลองเช็กว่า backend ยังทำงานอยู่";
  }
  if (error instanceof SyntaxError) {
    return "เซิร์ฟเวอร์ตอบกลับมาไม่สมบูรณ์";
  }
  return error instanceof Error && error.message ? error.message : fallbackText;
}

function formatHeartbeatStatus(lastHeartbeatAt, secondsSinceHeartbeat) {
  if (!lastHeartbeatAt) {
    return "-";
  }
  const formattedTime = formatDate(lastHeartbeatAt);
  if (secondsSinceHeartbeat === null || secondsSinceHeartbeat === undefined) {
    return formattedTime;
  }
  return `${formattedTime} (${secondsSinceHeartbeat} วินาทีก่อน)`;
}

function formatLatencyMs(latencyMs) {
  if (latencyMs === null || latencyMs === undefined || Number.isNaN(Number(latencyMs))) {
    return "-";
  }
  return `${Math.round(Number(latencyMs))} ms`;
}
