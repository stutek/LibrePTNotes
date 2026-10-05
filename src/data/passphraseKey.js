// Iz LibrePT (src/data/passphraseKey.js): ključ AES-GCM iz gesla. Parametri so enaki, da se
// šifrirana datoteka odpre z istim geslom v obeh aplikacijah: PBKDF2-HMAC-SHA-256, 600.000 ponovitev,
// 16-bajtna sol, 256-bitni ključ. Ključ ni izvozljiv, zato ga skript na strani ne more prebrati.
// `cryptoImpl` je argument, da je modul preizkusljiv v Nodu (webcrypto).

export const KDF_ITERATIONS = 600000;
export const KDF_HASH = "SHA-256";
export const SALT_BYTES = 16;
export const IV_BYTES = 12; // 96 bitov, kolikor določa AES-GCM; nov naključen IV pri vsakem šifriranju

export function toBase64(bytes) {
  let binary = "";
  for (const byte of new Uint8Array(bytes)) binary += String.fromCharCode(byte);
  return btoa(binary);
}

export function fromBase64(text) {
  const binary = atob(text);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return bytes;
}

export function randomSalt(cryptoImpl = globalThis.crypto) {
  return cryptoImpl.getRandomValues(new Uint8Array(SALT_BYTES));
}

export function randomIv(cryptoImpl = globalThis.crypto) {
  return cryptoImpl.getRandomValues(new Uint8Array(IV_BYTES));
}

// `iterations` je argument, ker se datoteka odpre s številom, s katerim je bila napisana.
export async function deriveAesKey(passphrase, salt, { iterations = KDF_ITERATIONS, extractable = false, cryptoImpl = globalThis.crypto } = {}) {
  const material = await cryptoImpl.subtle.importKey("raw", new TextEncoder().encode(passphrase), "PBKDF2", false, ["deriveKey"]);
  return cryptoImpl.subtle.deriveKey(
    { name: "PBKDF2", salt, iterations, hash: KDF_HASH },
    material,
    { name: "AES-GCM", length: 256 },
    extractable,
    ["encrypt", "decrypt"],
  );
}

// Šest besed iz kratkega seznama: trener jo lahko prepiše na papir, zato je berljiva, ne naključni
// znaki. Seznam je enak kot v LibrePT.
const PASSPHRASE_WORDS = [
  "anchor", "barbell", "cadence", "deadlift", "elbow", "flywheel", "gravity", "hinge",
  "impulse", "jumprope", "kettle", "lever", "mobility", "nordic", "overhead", "posture",
  "quadrant", "rowing", "sprint", "tempo", "unrack", "vertical", "warmup", "zercher",
];

export function generatePassphrase(cryptoImpl = globalThis.crypto, wordCount = 6) {
  const picks = new Uint32Array(wordCount);
  cryptoImpl.getRandomValues(picks);
  return Array.from(picks, (value) => PASSPHRASE_WORDS[value % PASSPHRASE_WORDS.length]).join("-");
}
