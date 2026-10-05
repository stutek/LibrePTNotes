// Varnostna kopija: vsebina (stranke in zapisi) v šifrirani ovojnici LibrePT (backupEncryption.js).
// Brez čistega JSON-a: kopija zapusti telefon, zato je vedno šifrirana. Google Drive ni vključen
// (TODO.md §3). Vsebina nosi `app`, da obnovitev zavrne datoteko druge aplikacije.
import { formatDateTime } from "../domain/dates.js";
import { decryptBackup, encryptBackup, isEncryptedBackup } from "./backupEncryption.js";
import { backupKeyForWriting } from "./backupKeyStore.js";
import { fromBase64 } from "./passphraseKey.js";

/** Isti zapis ovojnice kot šifrirana kopija v LibrePT (BACKUP_FORMATS[6]). */
export const ENCRYPTED_BACKUP_FORMAT = 6;
export const APP_ID = "libreptnotes";
export const PAYLOAD_VERSION = 1;

export class BackupError extends Error {
  constructor(code) {
    super(code);
    this.code = code; // no-password | bad-file | foreign | wrong-password | cancelled
  }
}

export function buildBackupPayload({ clients, notes }, { now = new Date() } = {}) {
  return { app: APP_ID, schemaVersion: PAYLOAD_VERSION, exportedAt: now.toISOString(), clients, notes };
}

/** Datoteka kopije za trenutno stanje; vrže BackupError("no-password"), če gesla ni. */
export async function createBackup({ store, keyStore, now = new Date(), cryptoImpl = globalThis.crypto }) {
  const writing = await backupKeyForWriting(keyStore);
  if (!writing) throw new BackupError("no-password");
  const payload = buildBackupPayload(await store.exportData(), { now });
  const envelope = await encryptBackup(payload, { ...writing, formatVersion: ENCRYPTED_BACKUP_FORMAT, cryptoImpl });
  return { filename: `libreptnotes-${formatDateTime(now).slice(0, 10)}.json`, text: JSON.stringify(envelope) };
}

function parseEnvelope(text) {
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new BackupError("bad-file");
  }
  // Neznana različica je zavrnitev, ne ugibanje: ovojnica novejše različice se ne sme brati kot prazna baza.
  if (!isEncryptedBackup(parsed) || parsed.formatVersion !== ENCRYPTED_BACKUP_FORMAT) throw new BackupError("bad-file");
  return parsed;
}

function bytesEqual(a, b) {
  return a.length === b.length && a.every((v, i) => v === b[i]);
}

function sameSalt(record, envelope) {
  try {
    return Boolean(record?.salt) && bytesEqual(new Uint8Array(record.salt), fromBase64(envelope.salt));
  } catch {
    return false;
  }
}

/**
 * Odpre datoteko kopije in vrne `{clients, notes}`. Shranjeni ključ se uporabi, če ima datoteka isto
 * sol; sicer (nova naprava, drugo geslo) se vpraša za geslo prek `askPassword(envelope)`, ki vrne
 * ključ ali null, če je trener odnehal.
 */
export async function readBackup(text, { keyStore, askPassword, cryptoImpl = globalThis.crypto }) {
  const envelope = parseEnvelope(text);
  const record = await keyStore.read();
  let payload = null;
  if (sameSalt(record, envelope)) {
    try {
      payload = await decryptBackup(envelope, { key: record.key, cryptoImpl });
    } catch {
      payload = null;
    }
  }
  if (!payload) {
    const key = await askPassword(envelope);
    if (!key) throw new BackupError("cancelled");
    try {
      payload = await decryptBackup(envelope, { key, cryptoImpl });
    } catch {
      throw new BackupError("wrong-password");
    }
  }
  if (payload?.app !== APP_ID || !Array.isArray(payload.clients) || !Array.isArray(payload.notes)) throw new BackupError("foreign");
  return { clients: payload.clients, notes: payload.notes };
}

/** Obnovitev zamenja vse: najprej odpre in preveri datoteko, šele nato vpraša in zamenja. */
export async function restoreBackup(text, { store, keyStore, askPassword, confirmReplace, cryptoImpl }) {
  const data = await readBackup(text, { keyStore, askPassword, cryptoImpl });
  if (!(await confirmReplace(data))) throw new BackupError("cancelled");
  await store.importData(data);
  return { clients: data.clients.length, notes: data.notes.length };
}
