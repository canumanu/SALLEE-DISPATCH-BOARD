/* Sallee Dispatch Board - minimal service worker.
   Purpose: make the app installable as a PWA and let the board shell still
   open when offline. Deliberately does NOT cache or intercept anything
   cross-origin (Microsoft Graph/SharePoint, the Load Board's orders.json,
   the MSAL CDN script) - those must always go to the network so sign-in
   and sync keep working exactly as before. */

const CACHE_NAME = 'sallee-dispatch-shell-v1';
const APP_SHELL = [
  './',
  './index.html',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-maskable-192.png',
  './icons/icon-maskable-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== location.origin) return; // never touch cross-origin requests

  if (req.mode === 'navigate') {
    // Loading the app itself: prefer the network (fresh code), fall back to
    // the cached shell only when offline.
    event.respondWith(
      fetch(req).catch(() => caches.match('./index.html'))
    );
    return;
  }

  // Static same-origin assets (icons, manifest): cache-first.
  event.respondWith(
    caches.match(req).then((cached) => cached || fetch(req))
  );
});
