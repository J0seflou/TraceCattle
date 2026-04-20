/* ══════════ Trace Cattle - Service Worker (sin caché) ══════════ */

// Limpiar todos los cachés anteriores al activar
self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k))))
  );
  self.clients.claim();
});

// Sin caché: todas las peticiones van directo a la red
self.addEventListener('fetch', (event) => {
  event.respondWith(fetch(event.request));
});
