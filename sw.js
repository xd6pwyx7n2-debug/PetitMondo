/* PetitMondo — consultation hors connexion des pages déjà ouvertes */
const CACHE = 'petitmondo-v2';
const BASE = new URL('./', self.location).pathname;
const ESSENTIELS = ['', 'assets/style.css', 'assets/commun.js', 'assets/carnet.js', 'assets/ville.js', 'assets/sprite.svg', 'assets/mondo.svg', 'carnet/'].map(p => BASE + p);

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ESSENTIELS)).catch(() => {}));
  self.skipWaiting();
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(k => Promise.all(k.filter(n => n !== CACHE).map(n => caches.delete(n)))));
  self.clients.claim();
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  const local = url.origin === location.origin;
  const tuiles = /basemaps\.cartocdn\.com|unpkg\.com|cdnjs\.cloudflare\.com|fonts\.(googleapis|gstatic)\.com/.test(url.host);
  if (!local && !tuiles) return;
  // Réseau d'abord, copie en cache, cache si hors connexion
  e.respondWith(fetch(req).then(r => {
    if (r.ok || r.type === 'opaque') { const copie = r.clone(); caches.open(CACHE).then(c => c.put(req, copie)); }
    return r;
  }).catch(() => caches.match(req, { ignoreSearch: local }).then(r => r || caches.match(BASE))));
});
