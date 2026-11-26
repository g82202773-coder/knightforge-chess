const CACHE = "knightforge-v4-1-coach";
const ASSETS = ["/", "/assets/styles.css", "/assets/pieces.js", "/assets/audio.js", "/assets/app.js", "/icon.svg"];

self.addEventListener("install", (ev) => {
  ev.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener("activate", (ev) => {
  ev.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((key) => key.startsWith("knightforge-") && key !== CACHE)
          .map((key) => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (ev) => {
  if (ev.request.method !== "GET" || ev.request.url.includes("/api/")) return;
  ev.respondWith(
    fetch(ev.request).catch(() => caches.match(ev.request))
  );
});
