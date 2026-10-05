// Iz LibrePT (src/data/backupKeyStore.js): kje je ključ varnostne kopije. Shrani se NEIZVOZLJIV
// ključ, sol in število ponovitev, nikoli geslo: kar bi se dalo spremeniti nazaj v geslo, bi z
// brskalnikovim profilom odklenilo vse kopije. Kdor drži odklenjen telefon, lahko kopijo naredi;
// zaščiti se datoteka, ki zapusti telefon, in ključ pred kopiranjem iz telefona.
// `store` ({read, write, clear}) je argument; privzeto v meta shrambi (createBackupKeyStore).
import { deriveKeyForEnvelope } from "./backupEncryption.js";
import { KDF_ITERATIONS, deriveAesKey, randomSalt } from "./passphraseKey.js";

const KEY = "backupKey";

export function createBackupKeyStore(backend) {
  return {
    // Zapis je v `value`, ker ima sam polje `key` (CryptoKey), meta shramba pa ima ključ `key`.
    read: async () => (await backend.get("meta", KEY))?.value,
    write: (record) => backend.put("meta", { key: KEY, value: record }),
    clear: () => backend.delete("meta", KEY),
  };
}

export async function hasBackupPassword(store) {
  return Boolean(await store.read());
}

// Nova sol pri vsaki nastavitvi: že shranjene datoteke ostanejo zaklenjene s starim geslom.
export async function setBackupPassword(
  passphrase,
  store,
  { cryptoImpl = globalThis.crypto, now = Date.now() } = {},
) {
  if (!passphrase) throw new Error("a backup password is required");
  const salt = randomSalt(cryptoImpl);
  const key = await deriveAesKey(passphrase, salt, { cryptoImpl });
  const record = { key, salt, iterations: KDF_ITERATIONS, setAt: now };
  await store.write(record);
  return record;
}

export async function backupKeyForWriting(store) {
  const record = await store.read();
  if (!record?.key) return null;
  return { key: record.key, salt: record.salt, iterations: record.iterations || KDF_ITERATIONS };
}

// Pot nove naprave: geslo, vpisano zdaj. Ključ se izpelje iz soli DATOTEKE, zato je enak tistemu, ki
// jo je zapisal; `remember` ga obdrži na tej napravi.
export async function unlockWithPassword(
  envelope,
  passphrase,
  store,
  { cryptoImpl = globalThis.crypto, remember = false, now = Date.now() } = {},
) {
  if (!passphrase) throw new Error("a backup password is required");
  const { key, salt, iterations } = await deriveKeyForEnvelope(envelope, passphrase, {
    cryptoImpl,
  });
  if (remember) await store.write({ key, salt, iterations, setAt: now });
  return { key, salt, iterations };
}

export async function forgetBackupPassword(store) {
  await store.clear();
}
