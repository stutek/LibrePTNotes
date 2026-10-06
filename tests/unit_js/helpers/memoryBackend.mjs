// Enako vmesnik kot src/data/idbBackend.js, v pomnilniku, da se logika shrambe preizkusi v Nodu.
export function memoryBackend() {
  const stores = { clients: new Map(), notes: new Map(), meta: new Map() };
  const keyOf = (name, value) => (name === "meta" ? value.key : value.id);
  const clone = (v) => structuredClone(v);
  return {
    stores,
    async getAll(name) {
      return [...stores[name].values()].map(clone);
    },
    // Kot IDBIndex.getAll: vrstice, katerih polje `index` je enako `key`.
    async getAllByIndex(name, index, key) {
      return [...stores[name].values()].filter((v) => v[index] === key).map(clone);
    },
    async get(name, key) {
      const v = stores[name].get(key);
      return v === undefined ? undefined : clone(v);
    },
    async put(name, value) {
      stores[name].set(keyOf(name, value), clone(value));
    },
    async delete(name, key) {
      stores[name].delete(key);
    },
    async replaceAll({ clients, notes, meta }) {
      for (const [name, rows] of [
        ["clients", clients],
        ["notes", notes],
        ["meta", meta],
      ]) {
        stores[name].clear();
        for (const row of rows) stores[name].set(keyOf(name, row), clone(row));
      }
    },
  };
}
