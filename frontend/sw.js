/* ══════════ Trace Cattle - Service Worker ══════════ */

const CACHE_NAME = 'tracecattle-v1';
const STATIC_ASSETS = [
  '/',
  '/css/styles.css',
  '/js/app.js',
  '/js/auth.js',
  '/js/animals.js',
  '/js/events.js',
  '/js/biometrics.js',
  '/js/audit.js',
  '/js/search.js',
  '/manifest.json',
];

// Instalar: cachear archivos estáticos
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Activar: limpiar caches viejos
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch: network first para API, cache first para estáticos
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Peticiones a la API siempre van a la red
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(event.request));
    return;
  }

  // Archivos estáticos: cache first, luego red
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((response) => {
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      });
    })
  );
});
