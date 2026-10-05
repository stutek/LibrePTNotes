import assert from "node:assert/strict";
import { createHash, webcrypto } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import vm from "node:vm";

const SRC = new URL("../../../src/", import.meta.url).pathname;
const SW_SOURCE = readFileSync(join(SRC, "sw.js"), "utf8");
const sha = (text) => createHash("sha256").update(text).digest("hex");

// Zažene sw.js z lažnimi self, caches in fetch; vrne pomočnike za sprožanje dogodkov.
function boot({ site, existing = {} }) {
  const stores = new Map(Object.entries(existing).map(([k, v]) => [k, new Map(Object.entries(v))]));
  const handlers = {};
  const calls = { skipWaiting: 0, claim: 0, fetched: [] };
  const caches = {
    has: async (n) => stores.has(n),
    keys: async () => [...stores.keys()],
    delete: async (n) => stores.delete(n),
    open: async (n) => {
      if (!stores.has(n)) stores.set(n, new Map());
      const s = stores.get(n);
      return {
        put: async (url, response) => s.set(String(url), await response.text()),
        // Zahteve iz strani so absolutne pod /LibrePTNotes/, ključi so relativni kot v pravem Cache API.
        match: async (req) => {
          const raw = String(req.url ?? req).split("?")[0];
          const key = raw.includes("/LibrePTNotes/") ? `./${raw.split("/LibrePTNotes/")[1]}` : raw;
          return s.has(key) ? new Response(s.get(key)) : undefined;
        },
      };
    },
  };
  const fetch = async (input) => {
    const path = String(input.url ?? input).replace(/^\.\//, "");
    calls.fetched.push(path);
    return path in site ? new Response(site[path]) : new Response("", { status: 404 });
  };
  const self = {
    addEventListener: (type, fn) => {
      handlers[type] = fn;
    },
    skipWaiting: () => {
      calls.skipWaiting += 1;
    },
    clients: {
      claim: async () => {
        calls.claim += 1;
      },
    },
    location: { origin: "https://x.test" },
  };
  vm.runInNewContext(SW_SOURCE, { self, caches, fetch, crypto: webcrypto, URL, Response, console });
  const run = async (type, event = {}) => {
    let pending;
    await handlers[type]({
      ...event,
      waitUntil: (p) => {
        pending = p;
      },
    });
    return pending;
  };
  return { stores, calls, run, handlers };
}

const catalogOf = (files) =>
  JSON.stringify({
    algorithm: "SHA-256",
    files: Object.fromEntries(Object.entries(files).map(([p, t]) => [p, sha(t)])),
  });
const FILES = { "index.html": "<html>", "app.js": "js", "sub/x.css": "css", "sw.js": "worker" };
const site = (files = FILES, catalog = catalogOf(files)) => ({
  ...files,
  "integrity.json": catalog,
});

test("install prednaloži vsako datoteko iz kataloga v libreptnotes-v<N>, razen sw.js in kataloga", async () => {
  const sw = boot({ site: site() });
  await sw.run("install");
  const names = [...sw.stores.keys()];
  assert.equal(names.length, 1);
  assert.match(names[0], /^libreptnotes-v\d+$/);
  assert.deepEqual([...sw.stores.get(names[0]).keys()].sort(), [
    "./app.js",
    "./index.html",
    "./sub/x.css",
  ]);
});

test("install ne kliče skipWaiting: nova različica počaka na gumb Osveži", async () => {
  const sw = boot({ site: site() });
  await sw.run("install");
  // is the contract: index.html's shipped policy; an avoided side effect (stored XSS / silent version switch).
  assert.equal(sw.calls.skipWaiting, 0);
  await sw.handlers.message({ data: { type: "SKIP_WAITING" } });
  // is the contract: index.html's shipped policy; an avoided side effect (stored XSS / silent version switch).
  assert.equal(sw.calls.skipWaiting, 1);
  await sw.handlers.message({ data: { type: "drugo" } });
  // is the contract: index.html's shipped policy; an avoided side effect (stored XSS / silent version switch).
  assert.equal(sw.calls.skipWaiting, 1);
});

test("neujemanje SHA-256 prekine namestitev in ne pusti polnega predpomnilnika", async () => {
  const bad = catalogOf({ ...FILES, "app.js": "drugačen" });
  const sw = boot({ site: site(FILES, bad) });
  await assert.rejects(() => sw.run("install"), /SHA-256/);
  assert.deepEqual([...sw.stores.keys()], []);
});

test("manjkajoč ali neveljaven katalog prekine namestitev", async () => {
  await assert.rejects(() => boot({ site: FILES }).run("install"));
  await assert.rejects(() => boot({ site: site(FILES, '{"files": {}}') }).run("install"));
});

test("neuspela namestitev ne zbriše že obstoječega predpomnilnika iste različice", async () => {
  const name = await (async () => {
    const s = boot({ site: site() });
    await s.run("install");
    return [...s.stores.keys()][0];
  })();
  const sw = boot({
    site: site(FILES, catalogOf({ ...FILES, "app.js": "x" })),
    existing: { [name]: { "./app.js": "stari" } },
  });
  await assert.rejects(() => sw.run("install"));
  assert.equal(sw.stores.get(name).get("./app.js"), "stari");
});

test("activate briše samo stare libreptnotes-* predpomnilnike in prevzame strani", async () => {
  const probe = boot({ site: site() });
  await probe.run("install");
  const current = [...probe.stores.keys()][0];
  const sw = boot({
    site: site(),
    existing: { [current]: {}, "libreptnotes-v0": {}, "librept-v148": {}, tuj: {} },
  });
  await sw.run("activate");
  assert.deepEqual([...sw.stores.keys()].sort(), ["librept-v148", current, "tuj"].sort());
  // is the contract: index.html's shipped policy; an avoided side effect (stored XSS / silent version switch).
  assert.equal(sw.calls.claim, 1);
});

test("fetch: predpomnjena datoteka brez omrežja, naslov mape je index.html, tuji izvor ni prestrežen", async () => {
  const sw = boot({ site: site() });
  await sw.run("install");
  const respond = async (url, extra = {}) => {
    let result;
    const request = { url, method: "GET", mode: "cors", ...extra };
    sw.handlers.fetch({
      request,
      respondWith: (p) => {
        result = p;
      },
    });
    return result && (await (await result).text());
  };
  sw.calls.fetched.length = 0;
  assert.equal(await respond("https://x.test/LibrePTNotes/app.js?v=1"), "js");
  assert.equal(await respond("https://x.test/LibrePTNotes/", { mode: "navigate" }), "<html>");
  // is the contract: index.html's shipped policy; an avoided side effect (stored XSS / silent version switch).
  assert.equal(sw.calls.fetched.length, 0, "predpomnjeno ne gre na omrežje");
  assert.equal(await respond("https://drug.test/app.js"), undefined);
  assert.equal(await respond("https://x.test/LibrePTNotes/app.js", { method: "POST" }), undefined);
});

test("manifest ima relativne poti in svoje ime", () => {
  const m = JSON.parse(readFileSync(join(SRC, "manifest.webmanifest"), "utf8"));
  assert.equal(m.name, "LibrePTNotes");
  assert.equal(m.start_url, "./");
  assert.equal(m.scope, "./");
  for (const icon of m.icons) assert.ok(icon.src.startsWith("./"));
});
