# Vercel PWA Deploy

This project can deploy the mobile PWA as a static Vercel frontend. The ESP32 boards and AI services still talk to the FastAPI backend, so Vercel is only the UI layer.

## What Vercel Serves

- `/` -> `webui/index.html`
- `/app` and `/app/*` -> `webui/mobile.html`
- `/manifest.webmanifest` -> `webui/manifest.webmanifest`
- `/mobile-service-worker.js` -> `webui/mobile-service-worker.js`
- `/webui/*` -> static CSS, JS, icons, and SVG assets

## Required Backend

The PWA needs a public FastAPI origin for real device control. Good demo options:

- Cloudflare Tunnel to the local notebook FastAPI server.
- Render, Railway, Fly.io, or Cloud Run for a hosted FastAPI backend.
- A VPS with HTTPS.

The ESP32 control board and voice node must use the same public FastAPI base URL when testing outside the local LAN.

## Configure Backend URL

There are two supported ways:

1. Edit `webui/pwa-config.js` before deploying:

```js
window.NONGFA_API_BASE = "https://your-fastapi-backend.example.com";
```

2. Open the installed app once with a query parameter:

```text
https://your-vercel-app.vercel.app/app?apiBase=https://your-fastapi-backend.example.com
```

The app stores this value in `localStorage`. Users can also change it later in Settings -> Backend API.

## Vercel Steps

1. Import this repository into Vercel.
2. Use Framework Preset: `Other`.
3. Leave Build Command empty.
4. Leave Output Directory empty.
5. Deploy.
6. Open `/app` on HTTPS and run Settings diagnostics.
7. Set the backend URL, then test `/dashboard/status` from the PWA diagnostics panel.

## Still Required Before Public Demo

- Add auth for command/device endpoints before exposing the backend publicly.
- Add a trusted-origin CORS policy on FastAPI for the Vercel domain.
- Test installability on Android Chrome.
- Test Add to Home Screen and microphone permission on iOS Safari.
