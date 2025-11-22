// static/service-worker.js

const CACHE_VERSION = "v3";
const STATIC_CACHE = `static-${CACHE_VERSION}`;
const API_CACHE = `api-${CACHE_VERSION}`;
const HTML_CACHE = `html-${CACHE_VERSION}`;

const OFFLINE_URL = "/offline/";

// Файлы, которые хотим иметь в офлайне сразу
const STATIC_ASSETS = [
  "/",
  OFFLINE_URL,
  "/static/css/app.css",
  "/static/css/base.css",
  "/static/js/app.js",
  "/manifest.webmanifest",
];

// Утилита: лог с префиксом
function log(...args) {
  // закомментируй в проде, если не нужен лог
  // console.log("[SW]", ...args);
}

self.addEventListener("install", event => {
  log("install");
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => {
      return cache.addAll(STATIC_ASSETS).catch(() => null);
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  log("activate");
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(key => ![STATIC_CACHE, API_CACHE, HTML_CACHE].includes(key))
          .map(key => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// Очень простой helper: GET-запрос?
function isGetRequest(request) {
  return request.method === "GET";
}

// Наш домен?
function isSameOrigin(request) {
  return self.location.origin === new URL(request.url).origin;
}

// API-запрос?
function isApiRequest(request) {
  const url = new URL(request.url);
  return url.pathname.startsWith("/api/");
}

// HTML-страница?
function isHtmlRequest(request) {
  return request.headers.get("accept")?.includes("text/html");
}

self.addEventListener("fetch", event => {
  const { request } = event;

  if (!isGetRequest(request)) {
    return;
  }

  // 1) API: strategy "network-first с fallback в кеш"
  if (isApiRequest(request)) {
    event.respondWith(networkFirst(request, API_CACHE));
    return;
  }

  // 2) HTML-страницы: тоже network-first + офлайн-страница
  if (isSameOrigin(request) && isHtmlRequest(request)) {
    event.respondWith(
      networkFirst(request, HTML_CACHE, {
        fallbackUrl: OFFLINE_URL,
      })
    );
    return;
  }

  // 3) Всё остальное (CSS/JS/картинки) — cache-first
  event.respondWith(cacheFirst(request, STATIC_CACHE));
});

// --------- стратегии кеширования ---------

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) {
    return cached;
  }

  try {
    const response = await fetch(request);
    if (response && response.status === 200) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    // Если совсем всё плохо — пробуем офлайн-страницу
    if (isHtmlRequest(request)) {
      const fallback = await caches.match(OFFLINE_URL);
      if (fallback) return fallback;
    }
    throw err;
  }
}

async function networkFirst(request, cacheName, options = {}) {
  const cache = await caches.open(cacheName);

  try {
    const response = await fetch(request);
    if (response && response.status === 200) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    const cached = await cache.match(request);
    if (cached) {
      return cached;
    }

    if (options.fallbackUrl) {
      const fallback = await caches.match(options.fallbackUrl);
      if (fallback) return fallback;
    }

    throw err;
  }
}
