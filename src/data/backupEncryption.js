// Iz LibrePT (src/data/backupEncryption.js): šifrirana ovojnica varnostne kopije, v istem zapisu.
// Zunaj šifrirane vsebine je le to, kar bralnik potrebuje, da odpre škatlo: formatVersion, parametri
// KDF, sol, IV in en stavek besedila. Datum, število zapisov in imena so znotraj, pod overjanjem GCM.
// Ključ se izpelje iz gesla (passphraseKey.js), da se kopija odpre tudi na novem telefonu.
import { KDF_HASH, KDF_ITERATIONS, deriveAesKey, fromBase64, randomIv, toBase64 } from "./passphraseKey.js";

export const AES_GCM_CONTAINER = "aes-gcm";

// Besedilo je v angleščini in brez imen, kot v LibrePT: bere ga lahko podpora ali prihodnja različica.
const HINT = "Encrypted LibrePTNotes backup. Open it in LibrePTNotes with your backup password.";

export function isEncryptedBackup(parsed) {
  return Boolean(parsed) && typeof parsed === "object" && parsed.container === AES_GCM_CONTAINER && typeof parsed.ciphertext === "string";
}

export async function encryptBackup(payload, { key, salt, iterations = KDF_ITERATIONS, formatVersion, cryptoImpl = globalThis.crypto }) {
  if (!key) throw new Error("an encryption key is required to write an encrypted backup");
  if (!salt) throw new Error("the key's salt is required, or the file cannot be opened elsewhere");
  if (!formatVersion) throw new Error("the caller states the format version");
  const iv = randomIv(cryptoImpl);
  const ciphertext = await cryptoImpl.subtle.encrypt({ name: "AES-GCM", iv }, key, new TextEncoder().encode(JSON.stringify(payload)));
  return {
    formatVersion,
    container: AES_GCM_CONTAINER,
    kdf: { name: "PBKDF2", hash: KDF_HASH, iterations },
    salt: toBase64(salt),
    iv: toBase64(iv),
    ciphertext: toBase64(ciphertext),
    hint: HINT,
  };
}

// Napačen ključ in spremenjena datoteka sta pri GCM neločljiva, zato napaka pove obe možnosti.
export async function decryptBackup(envelope, { key, cryptoImpl = globalThis.crypto }) {
  if (!isEncryptedBackup(envelope)) throw new Error("not an encrypted backup");
  try {
    const plaintext = await cryptoImpl.subtle.decrypt({ name: "AES-GCM", iv: fromBase64(envelope.iv) }, key, fromBase64(envelope.ciphertext));
    return JSON.parse(new TextDecoder().decode(plaintext));
  } catch {
    throw new Error("wrong backup password, or the file was altered");
  }
}

// Parametre KDF bere iz datoteke, ne iz konstant te različice: datoteka z nižjim številom ponovitev
// se mora še vedno odpreti.
export async function deriveKeyForEnvelope(envelope, passphrase, { cryptoImpl = globalThis.crypto } = {}) {
  if (!isEncryptedBackup(envelope)) throw new Error("not an encrypted backup");
  const salt = fromBase64(envelope.salt);
  const iterations = envelope.kdf?.iterations || KDF_ITERATIONS;
  const key = await deriveAesKey(passphrase, salt, { iterations, cryptoImpl });
  return { key, salt, iterations };
}
