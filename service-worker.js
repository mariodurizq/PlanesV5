const VERSION = 'renta-shell-v36';
const APP_FILES = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icon-192.png',
  './icon-512.png',
  './icon-maskable-512.png',
  './apple-touch-icon.png',
  './brand/emblema-96.png',
  './brand/nombre-light.png',
  './brand/nombre-dark.png',
  './brand/nombre-white.png',
  './favicon.png',
  './vendor/leaflet.css?v=1',
  './vendor/leaflet.js?v=1',
  './plan-share.js?v=6',
  './fonts/inter-latin-400-normal.woff2',
  './fonts/inter-latin-600-normal.woff2',
  './fonts/space-grotesk-latin-700-normal.woff2'
];

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(VERSION);
    // uno a uno: si falta algún archivo, el resto se guarda igualmente
    await Promise.all(APP_FILES.map(f => cache.add(f).catch(() => {})));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(key => (key.startsWith('radar-shell-') || key.startsWith('renta-shell-')) && key !== VERSION).map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  // Never cache API calls, maps, photos, or third-party responses.
  if (url.origin !== self.location.origin) return;

  if (req.mode === 'navigate') {
    const esPortada = /\/(index\.html)?$/.test(url.pathname) && !/\/mejores\/$/.test(url.pathname);
    if (esPortada) {
      // Portada: siempre la versión nueva si hay red (espera como mucho 4 s); la guardada solo sin conexión o si la red tarda
      event.respondWith((async () => {
        const cache = await caches.open(VERSION);
        const red = fetch('./index.html', {cache: 'no-store'}).then(async fresh => {
          if (fresh && fresh.ok) await cache.put('./index.html', fresh.clone());
          return fresh;
        });
        const cached = await cache.match('./index.html');
        if (!cached) { try { return await red; } catch (e) { return Response.error(); } }
        const lento = new Promise(r => setTimeout(() => r(null), 4000));
        try {
          const fresh = await Promise.race([red, lento]);
          if (fresh && fresh.ok) return fresh;
        } catch (e) {}
        event.waitUntil(red.catch(() => {}));
        return cached.clone();
      })());
      return;
    }
    // Resto de páginas (plan, legal, listas…): la versión nueva si hay red; la guardada sin conexión
    event.respondWith((async () => {
      const cache = await caches.open(VERSION);
      try {
        const fresh = await fetch(req);
        if (fresh && fresh.ok) cache.put(url.pathname, fresh.clone());
        return fresh;
      } catch (e) {
        return (await cache.match(url.pathname)) || Response.error();
      }
    })());
    return;
  }

  // Datos (.json) y páginas: siempre la versión nueva si hay red; la guardada solo sin conexión.
  if (/\.(json|html)$/.test(url.pathname)) {
    event.respondWith((async () => {
      const cache = await caches.open(VERSION);
      try {
        const fresh = await fetch(req, {cache: 'no-store'});
        if (fresh && fresh.ok) cache.put(url.pathname, fresh.clone());
        return fresh;
      } catch (e) {
        return (await cache.match(url.pathname)) || Response.error();
      }
    })());
    return;
  }

  event.respondWith((async () => {
    const cache = await caches.open(VERSION);
    const cached = await cache.match(req);
    if (cached) return cached;
    try {
      const fresh = await fetch(req);
      if (fresh && fresh.ok) cache.put(req, fresh.clone());
      return fresh;
    } catch (e) {
      return cached || Response.error();
    }
  })());
});
