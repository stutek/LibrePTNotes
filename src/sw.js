// Service worker LibrePTNotes. Poti so relativne, zato deluje na kateri koli poti in domeni.
// Predpomnilnik se imenuje `libreptnotes-v<N>`; domena stutek.github.io je skupna z LibrePT, zato ime
// ne sme sovpadati z LibrePT-jevim (TODO.md §3: LibrePT briše tuje predpomnilnike).
const CACHE = "libreptnotes-v1";
const PRECACHE = [
  "./",
  "./index.html",
  "./app.js",
  "./app.css",
  "./i18n.js",
  "./data/idbBackend.js",
  "./data/store.js",
  "./domain/dates.js",
  "./domain/notes.js",
  "./ui/dom.js",
  "./ui/tabs.js",
  "./ui/clientList.js",
  "./manifest.webmanifest",
  "./icons/icon.svg",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./gesture/planPeek.js",
  "./gesture/planPeek.css",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      // Briše samo svoje stare različice, nikoli tujih predpomnilnikov.
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith("libreptnotes-") && k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

// Najprej predpomnilnik, v ozadju osvežitev: brez koraka gradnje ni številke različice, ki bi jo
// bilo treba dvigniti, nova različica pa pride ob naslednjem zagonu.
self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET" || new URL(request.url).origin !== self.location.origin) return;
  event.respondWith(
    caches.open(CACHE).then(async (cache) => {
      const cached = await cache.match(request, { ignoreSearch: true });
      const refresh = fetch(request)
        .then((response) => {
          if (response.ok) cache.put(request, response.clone());
          return response;
        })
        .catch(() => cached);
      return cached || refresh;
    }),
  );
});
