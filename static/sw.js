self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

// Minimal: network-first (no offline caching yet)
self.addEventListener("fetch", (event) => {
  event.respondWith(fetch(event.request));
});
