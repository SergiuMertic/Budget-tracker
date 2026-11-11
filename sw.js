// Service worker: keeps the app working without internet.
// Bump CACHE when any file changes so phones pick up the new version.
const CACHE = 'budget-v19';
const ASSETS = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icons/apple-touch-icon.png",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./fonts/barlow-latin-400-normal.woff2",
  "./fonts/barlow-latin-500-normal.woff2",
  "./fonts/barlow-latin-600-normal.woff2",
  "./fonts/barlow-latin-700-normal.woff2",
  "./fonts/barlow-semi-condensed-latin-600-normal.woff2",
  "./fonts/barlow-semi-condensed-latin-700-normal.woff2",
  "./vendor/pdfjs/pdf.min.mjs",
  "./vendor/pdfjs/pdf.worker.min.mjs"
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(ASSETS.map((u) => new Request(u, { cache: 'reload' }))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Ask the server every time (no-cache), so a new version shows up on the next open.
function fresh(req) {
  try { return fetch(new Request(req, { cache: 'no-cache' })); } catch (e) { return fetch(req); }
}

function timeout(ms) {
  return new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), ms));
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin) return;

  // The page itself: get the newest version when online, otherwise use the saved copy.
  if (req.mode === 'navigate') {
    event.respondWith(
      Promise.race([fresh(req), timeout(4000)])
        .then((res) => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((cache) => cache.put('./index.html', copy));
          }
          return res;
        })
        .catch(() => caches.match('./index.html').then((hit) => hit || fetch(req)))
    );
    return;
  }

  // Fonts, icons and the manifest: saved copy first.
  event.respondWith(caches.match(req).then((hit) => hit || fetch(req)));
});
