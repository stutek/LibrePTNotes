// IndexedDB za store.js. Baza `libreptnotes`; domena stutek.github.io je skupna z LibrePT, zato ime
// ne sme sovpadati z njegovim.
export const DB_NAME = "libreptnotes";
export const DB_VERSION = 1;

const promisify = (request) =>
  new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });

const done = (tx) =>
  new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error);
  });

export function openDb(factory = indexedDB) {
  return new Promise((resolve, reject) => {
    const request = factory.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      db.createObjectStore("clients", { keyPath: "id" });
      db.createObjectStore("notes", { keyPath: "id" }).createIndex("clientId", "clientId");
      db.createObjectStore("meta", { keyPath: "key" });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export function idbBackend(db) {
  const store = (name, mode = "readonly") => db.transaction(name, mode).objectStore(name);
  return {
    getAll: (name) => promisify(store(name).getAll()),
    // Bere prek indeksa (zapisi po clientId), ne vseh vrstic in filtra v pomnilniku.
    getAllByIndex: (name, index, key) => promisify(store(name).index(index).getAll(key)),
    get: (name, key) => promisify(store(name).get(key)),
    put: (name, value) => promisify(store(name, "readwrite").put(value)).then(() => {}),
    delete: (name, key) => promisify(store(name, "readwrite").delete(key)).then(() => {}),
    // Ena transakcija: obnovitev je ali cela ali nič.
    async replaceAll({ clients, notes, meta }) {
      const tx = db.transaction(["clients", "notes", "meta"], "readwrite");
      for (const [name, rows] of [
        ["clients", clients],
        ["notes", notes],
        ["meta", meta],
      ]) {
        const s = tx.objectStore(name);
        s.clear();
        for (const row of rows) s.put(row);
      }
      await done(tx);
    },
  };
}
