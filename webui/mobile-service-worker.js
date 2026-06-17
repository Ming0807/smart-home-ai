const CACHE_NAME = "nongfa-mobile-pwa-v12";
const APP_SHELL = [
  "/app",
  "/app/",
  "/webui/mobile.css?v=pwa-20260617-3",
  "/webui/pwa-config.js?v=pwa-20260617-3",
  "/webui/mobile-icons-fallback.js?v=pwa-20260617-3",
  "/webui/mobile.js?v=pwa-20260617-3",
  "/webui/assets/nongfa-icon.svg",
  "/webui/assets/nongfa-robot.svg",
  "/webui/assets/nongfa-icon-180.png",
  "/webui/assets/nongfa-icon-192.png",
  "/webui/assets/nongfa-icon-512.png",
  "/webui/assets/nongfa-icon-maskable-512.png",
  "/manifest.webmanifest"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(names.filter((name) => name !== CACHE_NAME).map((name) => caches.delete(name)))
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }

  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) {
    return;
  }

  const isMobileNavigation =
    event.request.mode === "navigate" && (url.pathname === "/app" || url.pathname === "/app/");
  const isMobileAsset =
    url.pathname === "/manifest.webmanifest" ||
    url.pathname === "/mobile-service-worker.js" ||
    url.pathname.startsWith("/webui/assets/") ||
    url.pathname === "/webui/mobile-icons-fallback.js" ||
    url.pathname === "/webui/mobile.css" ||
    url.pathname === "/webui/mobile.js";

  if (!isMobileNavigation && !isMobileAsset) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request).then((cached) => cached || caches.match("/app")))
  );
});
