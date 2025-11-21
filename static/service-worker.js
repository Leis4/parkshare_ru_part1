/* eslint-disable no-restricted-globals */

const STATIC_CACHE = "parkshare-static-v3";
const DYNAMIC_CACHE = "parkshare-dynamic-v3";
const OFFLINE_URL = "/offline/";

const STATIC_ASSETS = [
  "/",
  "/offline/",
  "/static/css/app.css",
  "/static/js/app.js",
  "/manifest.webmanifest"
  // Иконки попадут в кэш по мере использования браузером
];

function isSameOrigin(request) {
  return new URL(request.url).origin === self.location.origin;
}

self.addEventListener("install", (event) => {
  console.log("[SW] install");

  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
      .catch((err) => console.warn("[SW] pre-cache error", err))
  );
});

self.addEventListener("activate", (event) => {
  console.log("[SW] activate");

  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((key) => key !== STATIC_CACHE && key !== DYNAMIC_CACHE)
          .map((key) => {
            console.log("[SW] removing old cache", key);
            return caches.delete(key);
          })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Только GET
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // Не трогаем сторонние домены
  if (!isSameOrigin(request)) return;

  // HTML: network-first с оффлайн-фоллбеком
  if (request.mode === "navigate" || request.headers.get("accept")?.includes("text/html")) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Статика: cache-first
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // API: network-first с кэшом на всякий случай
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Всё остальное — мягкий cache-first
  event.respondWith(cacheFirst(request));
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    const cache = await caches.open(DYNAMIC_CACHE);
    cache.put(request, response.clone());
    return response;
  } catch (err) {
    // В случае ошибки просто пробуем offline.html для HTML-запросов
    if (request.headers.get("accept")?.includes("text/html")) {
      const offline = await caches.match(OFFLINE_URL);
      if (offline) return offline;
    }
    throw err;
  }
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    const cache = await caches.open(DYNAMIC_CACHE);
    cache.put(request, response.clone());
    return response;
  } catch (err) {
    const cached = await caches.match(request);
    if (cached) return cached;

    if (request.headers.get("accept")?.includes("text/html")) {
      const offline = await caches.match(OFFLINE_URL);
      if (offline) return offline;
    }
    throw err;
  }
}
