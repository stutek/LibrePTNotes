import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import { test } from "node:test";
import {
  deriveKeyForEnvelope,
  encryptBackup,
  isEncryptedBackup,
} from "../../../src/data/backupEncryption.js";
import {
  BackupError,
  createBackup,
  readBackup,
  restoreBackup,
} from "../../../src/data/backupFile.js";
import {
  createBackupKeyStore,
  forgetBackupPassword,
  hasBackupPassword,
  setBackupPassword,
  unlockWithPassword,
} from "../../../src/data/backupKeyStore.js";
import { KDF_ITERATIONS, generatePassphrase } from "../../../src/data/passphraseKey.js";
import { createStore } from "../../../src/data/store.js";
import { memoryBackend } from "../helpers/memoryBackend.mjs";

// Dve "napravi": vsaka ima svojo bazo in svoj shranjen ključ.
function device() {
  const backend = memoryBackend();
  return { backend, store: createStore(backend), keyStore: createBackupKeyStore(backend) };
}

async function seeded(dev) {
  const ana = await dev.store.addClient("Ana Novak");
  await dev.store.addNote(ana.id, "# Skrivnost\n**krepko**");
  await dev.store.addClient("Bor");
}

const never = async () => assert.fail("geslo se ne sme vprašati");

test("geslo: generirano geslo se izpiše v celoti; brez gesla kopije ni", async () => {
  assert.equal(generatePassphrase(webcrypto).split("-").length, 7);
  const dev = device();
  assert.equal(await hasBackupPassword(dev.keyStore), false);
  await assert.rejects(
    () => createBackup(dev),
    (e) => e instanceof BackupError && e.code === "no-password",
  );
});

test("ovojnica ima zapis LibrePT in ne razkrije vsebine", async () => {
  const dev = device();
  await seeded(dev);
  await setBackupPassword("a-b-c", dev.keyStore);
  const { text, filename } = await createBackup({ ...dev, now: new Date(2026, 9, 5, 11, 0) });
  const envelope = JSON.parse(text);
  assert.equal(filename, "libreptnotes-2026-10-05.json");
  assert.equal(envelope.formatVersion, 6);
  assert.equal(envelope.container, "aes-gcm");
  assert.deepEqual(envelope.kdf, { name: "PBKDF2", hash: "SHA-256", iterations: KDF_ITERATIONS });
  assert.deepEqual(Object.keys(envelope).sort(), [
    "ciphertext",
    "container",
    "formatVersion",
    "hint",
    "iv",
    "kdf",
    "salt",
  ]);
  assert.ok(isEncryptedBackup(envelope));
  assert.ok(!text.includes("Ana"), "ime ne sme biti v čistopisu");
  assert.ok(!text.includes("Skrivnost"));
});

test("shrani in obnovi na isti napravi (shranjen ključ, brez vprašanja)", async () => {
  const dev = device();
  await seeded(dev);
  await setBackupPassword("moje-geslo", dev.keyStore);
  const { text } = await createBackup(dev);
  const before = await dev.store.exportData();
  await dev.store.addClient("Nova");
  const counts = await restoreBackup(text, {
    ...dev,
    askPassword: never,
    confirmReplace: async () => true,
  });
  assert.deepEqual(counts, { clients: 2, notes: 1 });
  assert.deepEqual(await dev.store.exportData(), before);
});

test("nov telefon: geslo vpisano, ključ iz soli datoteke; remember ga obdrži", async () => {
  const old = device();
  await seeded(old);
  await setBackupPassword("moje-geslo", old.keyStore);
  const { text } = await createBackup(old);

  const fresh = device();
  let asked = 0;
  const askPassword = async (envelope) => {
    asked += 1;
    return (await unlockWithPassword(envelope, "moje-geslo", fresh.keyStore, { remember: true }))
      .key;
  };
  await restoreBackup(text, { ...fresh, askPassword, confirmReplace: async () => true });
  assert.equal(asked, 1);
  assert.deepEqual(await fresh.store.exportData(), await old.store.exportData());
  assert.equal(await hasBackupPassword(fresh.keyStore), true);
  // Drugič se ne vpraša več: shranjeni ključ ima sol datoteke.
  await restoreBackup(text, { ...fresh, askPassword: never, confirmReplace: async () => true });
});

test("napačno geslo: napaka, baza nespremenjena", async () => {
  const old = device();
  await seeded(old);
  await setBackupPassword("pravo", old.keyStore);
  const { text } = await createBackup(old);
  const fresh = device();
  await fresh.store.addClient("Obstoječa");
  const askPassword = async (envelope) =>
    (await unlockWithPassword(envelope, "napacno", fresh.keyStore)).key;
  await assert.rejects(
    () => restoreBackup(text, { ...fresh, askPassword, confirmReplace: async () => true }),
    (e) => e.code === "wrong-password",
  );
  assert.deepEqual(
    (await fresh.store.listClients()).map((c) => c.name),
    ["Obstoječa"],
  );
});

test("odnehanje pri geslu ali potrditvi ne spremeni baze", async () => {
  const old = device();
  await seeded(old);
  await setBackupPassword("g", old.keyStore);
  const { text } = await createBackup(old);
  const fresh = device();
  await fresh.store.addClient("Obstoječa");
  await assert.rejects(
    () =>
      restoreBackup(text, {
        ...fresh,
        askPassword: async () => null,
        confirmReplace: async () => true,
      }),
    (e) => e.code === "cancelled",
  );
  await assert.rejects(
    () => restoreBackup(text, { ...old, askPassword: never, confirmReplace: async () => false }),
    (e) => e.code === "cancelled",
  );
  assert.deepEqual(
    (await fresh.store.listClients()).map((c) => c.name),
    ["Obstoječa"],
  );
});

test("datoteke, ki niso naše, se zavrnejo", async () => {
  const dev = device();
  await setBackupPassword("g", dev.keyStore);
  const opts = { keyStore: dev.keyStore, askPassword: never };
  for (const bad of ["ni json", "{}", JSON.stringify({ formatVersion: 4, clients: [] })]) {
    await assert.rejects(
      () => readBackup(bad, opts),
      (e) => e.code === "bad-file",
      bad,
    );
  }
  // Pravilno šifrirana, a iz druge aplikacije (LibrePT): odpre se, vendar se zavrne.
  const record = await dev.keyStore.read();
  const envelope = await encryptBackup(
    { schemaVersion: 5, clients: [], notes: [] },
    { key: record.key, salt: record.salt, formatVersion: 6 },
  );
  await assert.rejects(
    () => readBackup(JSON.stringify(envelope), opts),
    (e) => e.code === "foreign",
  );
});

test("pozabi geslo odstrani ključ; datoteka ostane odprta z novim vnosom gesla", async () => {
  const dev = device();
  await setBackupPassword("g", dev.keyStore);
  await forgetBackupPassword(dev.keyStore);
  assert.equal(await hasBackupPassword(dev.keyStore), false);
});

test("ključ iz datoteke je enak ključu, ki jo je zapisal", async () => {
  const dev = device();
  await seeded(dev);
  await setBackupPassword("isto", dev.keyStore);
  const { text } = await createBackup(dev);
  const { key } = await deriveKeyForEnvelope(JSON.parse(text), "isto");
  assert.ok(key);
});

// Odklep z geslom, kot ga vrne dialog: ključ je izpeljan, ničesar še ni shranjenega.
const typed = (password, remember) => async (envelope) => ({
  ...(await unlockWithPassword(envelope, password, createBackupKeyStore(memoryBackend()))),
  remember,
});

test("napačno geslo z obkljukanim »zapomni si« ne prepiše shranjenega gesla in ne shrani drugega", async () => {
  const other = device();
  await seeded(other);
  await setBackupPassword("pravo-geslo", other.keyStore);
  const { text } = await createBackup(other);

  const mine = device();
  const before = await setBackupPassword("moje-geslo", mine.keyStore);
  await assert.rejects(
    () =>
      restoreBackup(text, {
        ...mine,
        askPassword: typed("zgresen-vnos", true),
        confirmReplace: async () => true,
      }),
    (e) => e.code === "wrong-password",
  );
  const after = await mine.keyStore.read();
  assert.deepEqual([...after.salt], [...before.salt], "sol (torej ključ) je nespremenjena");
  assert.equal(after.setAt, before.setAt);
});

test("na novi napravi se ključ iz datoteke shrani šele po uspešnem odklepu", async () => {
  const old = device();
  await seeded(old);
  await setBackupPassword("pravo-geslo", old.keyStore);
  const { text } = await createBackup(old);

  const fresh = device();
  await assert.rejects(
    () =>
      restoreBackup(text, {
        ...fresh,
        askPassword: typed("napacno", true),
        confirmReplace: async () => true,
      }),
    (e) => e.code === "wrong-password",
  );
  assert.equal(await hasBackupPassword(fresh.keyStore), false, "po napaki ni shranjeno nič");
  await restoreBackup(text, {
    ...fresh,
    askPassword: typed("pravo-geslo", true),
    confirmReplace: async () => true,
  });
  assert.equal(await hasBackupPassword(fresh.keyStore), true);
  await restoreBackup(text, { ...fresh, askPassword: never, confirmReplace: async () => true });
});

test("že nastavljeno geslo naprave se ob odklepu druge datoteke nikoli ne prepiše", async () => {
  const old = device();
  await seeded(old);
  await setBackupPassword("tuje-geslo", old.keyStore);
  const { text } = await createBackup(old);

  const mine = device();
  const before = await setBackupPassword("moje-geslo", mine.keyStore);
  await restoreBackup(text, {
    ...mine,
    askPassword: typed("tuje-geslo", true),
    confirmReplace: async () => true,
  });
  assert.deepEqual([...(await mine.keyStore.read()).salt], [...before.salt]);
});

test("kopija novejše različice se zavrne z lastno kodo, ne kot »ni kopija«", async () => {
  const dev = device();
  await assert.rejects(
    () =>
      readBackup(JSON.stringify({ formatVersion: 7, container: "aes-gcm", ciphertext: "x" }), {
        keyStore: dev.keyStore,
        askPassword: never,
      }),
    (e) => e.code === "newer",
  );
});
