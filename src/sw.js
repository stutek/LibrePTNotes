// Service worker LibrePTNotes. Poti so relativne, zato deluje na kateri koli poti in domeni.
//
// Predpomnilnik je ena celota: install prenese vsako datoteko iz /integrity.json (gradnja jo ustvari),
// preveri SHA-256 in šele nato je različica pripravljena; ob kateri koli napaki ostane stara različica.
// Vzorec je iz LibrePT (src/sw/precache.js, integrity.js), a brez seznama datotek v kodi: seznam je
// katalog, zato nova datoteka ne more manjkati.
//
// Ime `libreptnotes-v<N>`: N dvigne gradnja ali lastnik ob spremembi datotek v src/.
// Domena stutek.github.io je skupna z LibrePT, zato ime nikoli ne sovpada z njegovim `librept-v…`,
// in briše se samo `libreptnotes-*`.
const CACHE_VERSION = 1;
const CACHE_PREFIX = "libreptnotes-";
const CACHE = `${CACHE_PREFIX}v${CACHE_VERSION}`;
const CATALOG = "integrity.json";

async function sha256Hex(buffer) {
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function loadCatalog() {
  const response = await fetch(`./${CATALOG}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`${CATALOG}: ${response.status}`);
  const catalog = await response.json();
  if (catalog?.algorithm !== "SHA-256" || !catalog.files || typeof catalog.files !== "object")
    throw new Error(`${CATALOG}: neveljaven zapis`);
  return catalog.files;
}

async function precache() {
  const files = await loadCatalog();
  // sw.js brskalnik preverja sam; katalog se ne hešira sam.
  const paths = Object.keys(files).filter((p) => p !== "sw.js" && p !== CATALOG);
  const existed = await caches.has(CACHE);
  const cache = await caches.open(CACHE);
  try {
    await Promise.all(
      paths.map(async (path) => {
        const response = await fetch(`./${path}`, { cache: "no-store" });
        if (!response.ok) throw new Error(`${path}: ${response.status}`);
        if ((await sha256Hex(await response.clone().arrayBuffer())) !== files[path])
          throw new Error(`${path}: neujemanje SHA-256`);
        await cache.put(`./${path}`, response);
      }),
    );
  } catch (error) {
    // Pol napolnjen predpomnilnik bi mešal različice; star (že aktiven) ostane nedotaknjen.
    if (!existed) await caches.delete(CACHE);
    throw error;
  }
}

// Brez skipWaiting ob namestitvi: nova različica počaka, stran pokaže trak in pošlje SKIP_WAITING.
// Prva namestitev nima česa čakati in se aktivira sama.
self.addEventListener("install", (event) => event.waitUntil(precache()));

self.addEventListener("message", (event) => {
  if (event.data?.type === "SKIP_WAITING") self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      // Briše samo svoje stare različice, nikoli tujih predpomnilnikov.
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => k.startsWith(CACHE_PREFIX) && k !== CACHE)
            .map((k) => caches.delete(k)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

// Predpomnilnik najprej, brez osvežitve posameznih datotek (ta bi mešala različice); brez zadetka
// gre zahteva na omrežje. Brez povezave se naslov mape pokaže kot index.html.
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  event.respondWith(
    caches.open(CACHE).then(async (cache) => {
      const hit = await cache.match(request, { ignoreSearch: true });
      if (hit) return hit;
      if (request.mode === "navigate" && url.pathname.endsWith("/")) {
        const shell = await cache.match("./index.html");
        if (shell) return shell;
      }
      return fetch(request);
    }),
  );
});
