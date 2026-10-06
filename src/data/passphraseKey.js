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
export async function deriveAesKey(
  passphrase,
  salt,
  { iterations = KDF_ITERATIONS, extractable = false, cryptoImpl = globalThis.crypto } = {},
) {
  const material = await cryptoImpl.subtle.importKey(
    "raw",
    new TextEncoder().encode(passphrase),
    "PBKDF2",
    false,
    ["deriveKey"],
  );
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
  "anchor",
  "barbell",
  "cadence",
  "deadlift",
  "elbow",
  "flywheel",
  "gravity",
  "hinge",
  "impulse",
  "jumprope",
  "kettle",
  "lever",
  "mobility",
  "nordic",
  "overhead",
  "posture",
  "quadrant",
  "rowing",
  "sprint",
  "tempo",
  "unrack",
  "vertical",
  "warmup",
  "zercher",
];

// Naključno celo število v [0, n) brez pristranosti (zavrača vrednosti, ki bi ga izkrivile).
function randomBelow(n, cryptoImpl) {
  const limit = 0x100000000 - (0x100000000 % n);
  const box = new Uint32Array(1);
  do cryptoImpl.getRandomValues(box);
  while (box[0] >= limit);
  return box[0] % n;
}

// Znaki brez dvoumnih (0/o, 1/l/i), da se niz da prepisati s papirja.
const SUFFIX_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789";
const SUFFIX_LENGTH = 8;

/**
 * Geslo za kopijo: šest RAZLIČNIH besed in naključen niz. Samo besede iz seznama 24 (kot v LibrePT)
 * so dale ~27 bitov in so se ponavljale; brez ponavljanja je ~25 bitov, zato niz doda ~39 bitov
 * (31^8), skupaj ~66 bitov, kar ob 600.000 ponovitvah PBKDF2 ni več preprosto ugibati. Ovojnica ostane
 * enaka LibrePT: geslo je v njej le vnos v izpeljavo ključa.
 */
export function generatePassphrase(cryptoImpl = globalThis.crypto, wordCount = 6) {
  const pool = [...PASSPHRASE_WORDS];
  const words = [];
  for (let i = 0; i < wordCount; i += 1) {
    words.push(pool.splice(randomBelow(pool.length, cryptoImpl), 1)[0]);
  }
  const suffix = Array.from(
    { length: SUFFIX_LENGTH },
    () => SUFFIX_ALPHABET[randomBelow(SUFFIX_ALPHABET.length, cryptoImpl)],
  ).join("");
  return [...words, suffix].join("-");
}

/** Lastno geslo: "short" (pod 8 znaki, zavrne), "weak" (pod 12, opozori), sicer null. */
export function passphraseProblem(text) {
  const length = [...String(text ?? "").trim()].length;
  if (length < 8) return "short";
  if (length < 12) return "weak";
  return null;
}
