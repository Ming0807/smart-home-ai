function revokeAudioObjectUrl(audioElement) {
  const previousUrl = audioElement.dataset.objectUrl;
  if (previousUrl) {
    URL.revokeObjectURL(previousUrl);
    delete audioElement.dataset.objectUrl;
  }
}

function attachAudioBlob(audioElement, blobUrl) {
  revokeAudioObjectUrl(audioElement);
  audioElement.dataset.objectUrl = blobUrl;
  audioElement.src = blobUrl;
  audioElement.load();
}

async function fetchAudioBlobUrl(url) {
  const bustUrl = `${url}${url.includes("?") ? "&" : "?"}v=${Date.now()}`;
  const response = await fetch(bustUrl, {
    cache: "no-store",
    headers: { Accept: "audio/mpeg" },
  });

  if (!response.ok) {
    throw new Error(`audio request failed: ${response.status}`);
  }

  const audioBlob = await response.blob();
  if (!audioBlob.size) {
    throw new Error("audio blob is empty");
  }

  return URL.createObjectURL(audioBlob);
}

async function loadAudioWithRetry(
  audioElement,
  url,
  autoplay = false,
  statusElement = null,
  attempt = 0,
  recoveryText = null
) {
  const maxAttempts = 24;
  if (statusElement) {
    statusElement.textContent = `กำลังเตรียมเสียง... (${attempt + 1}/${maxAttempts})`;
  }

  try {
    await ensureAudioTokenReady(url);
    const blobUrl = await fetchAudioBlobUrl(url);
    attachAudioBlob(audioElement, blobUrl);

    await new Promise((resolve, reject) => {
      const onLoaded = () => {
        cleanup();
        resolve();
      };
      const onError = () => {
        cleanup();
        reject(new Error("audio not playable"));
      };
      const cleanup = () => {
        audioElement.removeEventListener("canplaythrough", onLoaded);
        audioElement.removeEventListener("error", onError);
      };

      audioElement.addEventListener("canplaythrough", onLoaded, { once: true });
      audioElement.addEventListener("error", onError, { once: true });
    });

    if (statusElement) {
      statusElement.textContent = autoplay ? "เสียงพร้อมแล้ว กำลังเล่น..." : "เสียงพร้อมแล้ว";
    }

    if (autoplay) {
      await audioElement.play().catch(() => {});
      if (statusElement) {
        statusElement.textContent = "เล่นเสียงอัตโนมัติแล้ว";
      }
    }
  } catch (error) {
    const isSuperseded = error instanceof Error && error.message === "audio superseded";
    if (isSuperseded) {
      if (statusElement) {
        statusElement.textContent = "เสียงนี้ถูกแทนที่ด้วยคำตอบล่าสุดแล้ว";
      }
      return;
    }

    if (attempt < maxAttempts - 1) {
      await sleep(750);
      return loadAudioWithRetry(audioElement, url, autoplay, statusElement, attempt + 1, recoveryText);
    }

    if (recoveryText) {
      try {
        if (statusElement) {
          statusElement.textContent = "กำลังสร้างเสียงใหม่อีกครั้ง...";
        }
        const regeneratedAudioUrl = await requestSpeechAudioUrl(recoveryText);
        return loadAudioWithRetry(audioElement, regeneratedAudioUrl, autoplay, statusElement, 0, null);
      } catch (recoveryError) {
        // Final error state below.
      }
    }

    if (statusElement) {
      statusElement.textContent = "ยังสร้างเสียงไม่สำเร็จ ลองใหม่อีกครั้งได้";
    }
  }
}
