const VERSION = 'renta-shell-v31';
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
  './vendor/leaflet.css?v=1',
  './vendor/leaflet.js?v=1',
  './plan-share.js?v=5',
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
      // Portada: se abre al instante desde la copia guardada y se actualiza por detrás.
      // Si lo descargado es distinto, se avisa a la página («Hay una versión nueva»).
      event.respondWith((async () => {
        const cache = await caches.open(VERSION);
        const cached = await cache.match('./index.html');
        const refresh = (async () => {
          const fresh = await fetch('./index.html', {cache: 'no-store'});
          if (!fresh || !fresh.ok) return fresh;
          let changed = false;
          if (cached) { try { const [a, b] = await Promise.all([cached.clone().text(), fresh.clone().text()]); changed = a !== b; } catch (e) {} }
          await cache.put('./index.html', fresh.clone());
          if (changed) setTimeout(async () => {
            const cs = await self.clients.matchAll({type: 'window'});
            cs.forEach(c => c.postMessage({type: 'renta-nueva-version'}));
          }, 2500);
          return fresh;
        })();
        if (cached) { event.waitUntil(refresh.catch(() => {})); return cached.clone(); }
        try { return await refresh; } catch (e) { return Response.error(); }
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
