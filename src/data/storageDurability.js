// src/data/storageDurability.js — prosi brskalnik, naj IndexedDB ne pobriše ob pomanjkanju prostora.
// Brez navigator.storage.persist() je shramba »best-effort«: brskalnik jo sme zbrisati, trenerjevi zapisi
// pa so le v njej (nič ne gre na strežnik). Izid je poštena beseda, ne obljuba: brskalnik lahko zavrne.
// `storage` je argument (privzeto navigator.storage), da je vsaka veja preizkusljiva v Nodu.
export async function requestDurableStorage(
  storage = typeof navigator === "undefined" ? null : navigator.storage,
) {
  if (typeof storage?.persist !== "function") return "unsupported";
  try {
    if ((await storage.persisted?.()) === true) return "persistent";
  } catch {
    // Nevedeno stanje: vseeno poskusi prositi.
  }
  try {
    return (await storage.persist()) ? "persistent" : "best-effort";
  } catch {
    return "best-effort";
  }
}
