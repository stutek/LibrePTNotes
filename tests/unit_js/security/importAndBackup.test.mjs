import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
// Uvožena datoteka je nezaupljiva: tuje ali spremenjene datoteke se zavrnejo, ključi prototipa ne
// onesnažijo ničesar, ključ ni izvozljiv, ovojnica ne razkrije čistopisa.
import { test } from "node:test";
import { encryptBackup } from "../../../src/data/backupEncryption.js";
import { BackupError, createBackup, restoreBackup } from "../../../src/data/backupFile.js";
import {
  createBackupKeyStore,
  setBackupPassword,
  unlockWithPassword,
} from "../../../src/data/backupKeyStore.js";
import { deriveAesKey, randomSalt } from "../../../src/data/passphraseKey.js";
import { createStore } from "../../../src/data/store.js";
import { memoryBackend } from "../helpers/memoryBackend.mjs";

const PASSWORD = "varnostni-test-geslo";
const SECRET = "skrivna opomba o koleni";

function device() {
  const backend = memoryBackend();
  return { backend, store: createStore(backend), keyStore: createBackupKeyStore(backend) };
}

async function sealed(payload, { password = PASSWORD, formatVersion = 6, tamper = (e) => e } = {}) {
  const salt = randomSalt(webcrypto);
  const key = await deriveAesKey(password, salt);
  const envelope = await encryptBackup(payload, { key, salt, formatVersion });
  return JSON.stringify(tamper(envelope));
}

const good = (extra = {}) => ({
  app: "libreptnotes",
  schemaVersion: 1,
  clients: [{ id: "c", name: "Ana", created: 1 }],
  notes: [],
  ...extra,
});

async function restoreWith(dev, text) {
  let asked = 0;
  let confirmed = 0;
  const run = restoreBackup(text, {
    store: dev.store,
    keyStore: dev.keyStore,
    askPassword: async (envelope) => {
      asked += 1;
      return (await unlockWithPassword(envelope, PASSWORD, dev.keyStore)).key;
    },
    confirmReplace: async () => {
      confirmed += 1;
      return true;
    },
  });
  return { run, counts: () => ({ asked, confirmed }) };
}

async function rejection(dev, text) {
  const { run, counts } = await restoreWith(dev, text);
  const error = await run.then(
    () => null,
    (e) => e,
  );
  assert.ok(error instanceof BackupError, `pričakovan BackupError, dobljeno ${error}`);
  return { code: error.code, ...counts() };
}

test("zavrnjene datoteke ne spremenijo podatkov in ne pridejo do potrditve zamenjave", async () => {
  const dev = device();
  const ana = await dev.store.addClient("Ostane");
  await dev.store.addNote(ana.id, "ostane");
  const before = await dev.store.exportData();

  const cases = {
    "ni json": ["to ni json", "bad-file"],
    "navaden json brez ovojnice": [JSON.stringify(good()), "bad-file"],
    "nova različica oblike": [await sealed(good(), { formatVersion: 7 }), "newer"],
    "druga aplikacija": [await sealed(good({ app: "librept" })), "foreign"],
    "brez oznake aplikacije": [await sealed({ clients: [], notes: [] }), "foreign"],
    "zbirki nista seznama": [await sealed(good({ clients: "ne" })), "foreign"],
    "spremenjen šifrirni tekst": [
      await sealed(good(), { tamper: (e) => ({ ...e, ciphertext: flip(e.ciphertext) }) }),
      "wrong-password",
    ],
    "spremenjen IV": [
      await sealed(good(), { tamper: (e) => ({ ...e, iv: flip(e.iv) }) }),
      "wrong-password",
    ],
    "spremenjena sol": [
      await sealed(good(), { tamper: (e) => ({ ...e, salt: flip(e.salt) }) }),
      "wrong-password",
    ],
    "drugo geslo": [await sealed(good(), { password: "drugo-geslo" }), "wrong-password"],
    "grozeče število ponovitev": [
      await sealed(good(), {
        tamper: (e) => ({ ...e, kdf: { ...e.kdf, iterations: 4_000_000_000 } }),
      }),
      "bad-file",
    ],
    "brez števila ponovitev": [
      await sealed(good(), { tamper: (e) => ({ ...e, kdf: {} }) }),
      "bad-file",
    ],
  };
  for (const [name, [text, code]] of Object.entries(cases)) {
    const result = await rejection(dev, text);
    assert.equal(result.code, code, name);
    assert.equal(result.confirmed, 0, `${name}: potrditev zamenjave se ne sme vprašati`);
    assert.deepEqual(
      await dev.store.exportData(),
      before,
      `${name}: podatki se ne smejo spremeniti`,
    );
  }
});

function flip(base64) {
  const bytes = Buffer.from(base64, "base64");
  bytes[0] ^= 0xff;
  return bytes.toString("base64");
}

test("ključi prototipa v uvoženi datoteki ne onesnažijo ničesar", async () => {
  const hostile =
    '{"__proto__": {"polluted": "da"}, "constructor": {"prototype": {"polluted": "da"}}}';
  const client = JSON.parse(
    `{"id": "c1", "name": "Ana", "created": 1, "__proto__": {"polluted": "da"}, "constructor": ${hostile}}`,
  );
  const note = JSON.parse(
    `{"id": "n1", "clientId": "c1", "date": "2026-10-01 09:00", "created": 2, "text": "t", "__proto__": {"isAdmin": true}, "prototype": ${hostile}}`,
  );
  const payload = JSON.parse(
    `{"app": "libreptnotes", "schemaVersion": 1, "clients": [], "notes": [], "__proto__": {"polluted": "da"}, "constructor": ${hostile}}`,
  );
  payload.clients = [client];
  payload.notes = [note];

  const dev = device();
  const { run } = await restoreWith(dev, await sealed(payload));
  await run;

  assert.equal({}.polluted, undefined);
  assert.equal(Object.prototype.polluted, undefined);
  assert.equal({}.isAdmin, undefined);
  const [storedClient] = await dev.backend.getAll("clients");
  const [storedNote] = await dev.backend.getAll("notes");
  assert.deepEqual(Object.keys(storedClient).sort(), ["created", "id", "name"]);
  assert.deepEqual(Object.keys(storedNote).sort(), ["clientId", "created", "date", "id", "text"]);
  assert.equal(Object.getPrototypeOf(storedNote), Object.prototype);
  assert.equal(storedNote.isAdmin, undefined);
});

test("id-ji, ki so imena lastnosti Object.prototype, so navadni id-ji", async () => {
  const names = ["__proto__", "constructor", "toString", "hasOwnProperty"];
  const clients = names.map((id) => ({ id, name: `s-${id}`, created: 1 }));
  const notes = names.map((id) => ({
    id: `n-${id}`,
    clientId: id,
    date: "2026-10-01 09:00",
    created: 2,
    text: id,
  }));
  const dev = device();
  await dev.store.importData({ clients, notes });
  assert.deepEqual((await dev.store.listClients()).map((c) => c.id).sort(), [...names].sort());
  for (const id of names)
    assert.deepEqual(
      (await dev.store.listNotes(id)).map((n) => n.text),
      [id],
    );
  assert.equal({}.polluted, undefined);
});

test("neveljavni podatki v uvozu se zavrnejo in ne spremenijo baze", async () => {
  const dev = device();
  await dev.store.addClient("Ostane");
  const before = await dev.store.exportData();
  const bad = [
    { clients: [{ id: 1, name: "x" }], notes: [] },
    { clients: [{ id: "a", name: "   " }], notes: [] },
    {
      clients: [{ id: "a", name: "x" }],
      notes: [{ id: "n", clientId: "tuja", date: "2026-10-01 09:00", text: "" }],
    },
    { clients: [{ id: "a", name: "x" }], notes: [{ id: "n", clientId: "a", date: 5, text: "" }] },
    { clients: null, notes: [] },
  ];
  for (const data of bad) await assert.rejects(() => dev.store.importData(data));
  assert.deepEqual(await dev.store.exportData(), before);
});

test("ključ gesla ni izvozljiv in geslo se ne shrani", async () => {
  const dev = device();
  const record = await setBackupPassword(PASSWORD, dev.keyStore, { cryptoImpl: webcrypto });
  assert.equal(record.key.extractable, false);
  await assert.rejects(() => webcrypto.subtle.exportKey("raw", record.key));
  await assert.rejects(() => webcrypto.subtle.exportKey("jwk", record.key));

  const envelope = JSON.parse((await createBackup({ ...dev, cryptoImpl: webcrypto })).text);
  const other = device();
  const unlocked = await unlockWithPassword(envelope, PASSWORD, other.keyStore, {
    remember: true,
    cryptoImpl: webcrypto,
  });
  assert.equal(unlocked.key.extractable, false);
  assert.equal((await other.keyStore.read()).key.extractable, false);

  for (const d of [dev, other]) {
    const dump = JSON.stringify(
      [...d.backend.stores.meta.values()].map((m) => ({
        ...m,
        value: m.value && { ...m.value, key: "CryptoKey" },
      })),
    );
    assert.ok(!dump.includes(PASSWORD), "geslo ne sme biti v shrambi");
  }
});

test("ovojnica ne razkrije čistopisa, vsaka kopija ima nov IV", async () => {
  const dev = device();
  await setBackupPassword(PASSWORD, dev.keyStore, { cryptoImpl: webcrypto });
  const ana = await dev.store.addClient("Ana Novak");
  await dev.store.addNote(ana.id, SECRET);
  const first = (await createBackup({ ...dev, cryptoImpl: webcrypto })).text;
  const second = (await createBackup({ ...dev, cryptoImpl: webcrypto })).text;

  for (const leaked of [SECRET, "Ana Novak", PASSWORD, "clients", "notes", ana.id, "2026-"])
    assert.ok(!first.includes(leaked), leaked);
  const envelope = JSON.parse(first);
  assert.deepEqual(Object.keys(envelope).sort(), [
    "ciphertext",
    "container",
    "formatVersion",
    "hint",
    "iv",
    "kdf",
    "salt",
  ]);
  assert.equal(Buffer.from(envelope.iv, "base64").length, 12);
  assert.equal(Buffer.from(envelope.salt, "base64").length, 16);
  assert.notEqual(JSON.parse(second).iv, envelope.iv);
  assert.notEqual(JSON.parse(second).ciphertext, envelope.ciphertext);
});
