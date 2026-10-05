// Shramba LibrePTNotes: stranke, zapisi, odprti zavihki. Logika je neodvisna od IndexedDB; `backend`
// (idbBackend.js v brskalniku, tests/memoryBackend.js v testih) zna samo getAll/get/put/delete/replaceAll.
// Podatki ostanejo v brskalniku, nič ne gre na strežnik.
import { formatDateTime } from "../domain/dates.js";
import { sortNotes } from "../domain/notes.js";

const TABS_KEY = "tabs";
const CURRENT_PREFIX = "current:";
const COLLATOR = new Intl.Collator("sl");

export function createStore(
  backend,
  { now = () => new Date(), newId = () => crypto.randomUUID() } = {},
) {
  async function listNotes(clientId) {
    return sortNotes((await backend.getAll("notes")).filter((n) => n.clientId === clientId));
  }

  async function addClient(name) {
    const clean = String(name ?? "").trim();
    if (!clean) throw new Error("ime stranke je obvezno");
    const client = { id: newId(), name: clean, created: now().getTime() };
    await backend.put("clients", client);
    return client;
  }

  async function listClients() {
    return (await backend.getAll("clients")).sort((a, b) => COLLATOR.compare(a.name, b.name));
  }

  async function renameClient(id, name) {
    const clean = String(name ?? "").trim();
    if (!clean) throw new Error("ime stranke je obvezno");
    const client = await backend.get("clients", id);
    if (!client) throw new Error("stranka ne obstaja");
    await backend.put("clients", { ...client, name: clean });
  }

  async function setCurrentNote(clientId, noteId) {
    await backend.put("meta", { key: CURRENT_PREFIX + clientId, noteId });
  }

  // Zapis se lahko sestavi sinhrono (draftNote), da ga kretnja prikaže v istem opravilu, in shrani
  // pozneje (commitNote). Nov zapis je takoj trenutni: kretnja L ga odpre s trenutnim datumom.
  function draftNote(clientId, text = "") {
    const date = now();
    return { id: newId(), clientId, date: formatDateTime(date), created: date.getTime(), text };
  }

  async function commitNote(note) {
    await backend.put("notes", note);
    await setCurrentNote(note.clientId, note.id);
    return note;
  }

  const addNote = (clientId, text = "") => commitNote(draftNote(clientId, text));

  async function updateNoteText(id, text) {
    const note = await backend.get("notes", id);
    if (!note) throw new Error("zapis ne obstaja");
    await backend.put("notes", { ...note, text });
  }

  // Zapomnjen zapis, sicer najnovejši; null, če stranka nima zapisov.
  async function currentNote(clientId) {
    const notes = await listNotes(clientId);
    if (!notes.length) return null;
    const saved = await backend.get("meta", CURRENT_PREFIX + clientId);
    return notes.find((n) => n.id === saved?.noteId) || notes[notes.length - 1];
  }

  // Zbriše stranko, vse njene zapise, zapomnjen trenutni zapis in zavihek.
  async function deleteClient(id) {
    for (const note of await listNotes(id)) await backend.delete("notes", note.id);
    await backend.delete("meta", CURRENT_PREFIX + id);
    await closeTab(id);
    await backend.delete("clients", id);
  }

  // Zbriše zapis. Če je bil trenutni, postane trenutni prejšnji (starejši), sicer naslednji; vrne
  // id novega trenutnega zapisa ali null, ko stranka nima več zapisov.
  async function deleteNote(id) {
    const note = await backend.get("notes", id);
    if (!note) throw new Error("zapis ne obstaja");
    const before = await listNotes(note.clientId);
    const index = before.findIndex((n) => n.id === id);
    const wasCurrent = (await currentNote(note.clientId))?.id === id;
    await backend.delete("notes", id);
    const rest = before.filter((n) => n.id !== id);
    if (!rest.length) {
      await backend.delete("meta", CURRENT_PREFIX + note.clientId);
      return null;
    }
    if (!wasCurrent) return (await currentNote(note.clientId)).id;
    const next = rest[Math.max(0, index - 1)];
    await setCurrentNote(note.clientId, next.id);
    return next.id;
  }

  async function getTabs() {
    const saved = await backend.get("meta", TABS_KEY);
    const open = saved?.open || [];
    return { open, active: open.includes(saved?.active) ? saved.active : null };
  }

  async function saveTabs(open, active) {
    await backend.put("meta", { key: TABS_KEY, open, active });
  }

  async function openTab(clientId) {
    const { open } = await getTabs();
    await saveTabs(open.includes(clientId) ? open : [...open, clientId], clientId);
  }

  async function closeTab(clientId) {
    const { open, active } = await getTabs();
    await saveTabs(
      open.filter((id) => id !== clientId),
      active === clientId ? null : active,
    );
  }

  // null je seznam strank; zavihek, ki ni odprt, se ne izbere.
  async function setActiveTab(clientId) {
    const { open } = await getTabs();
    if (clientId !== null && !open.includes(clientId)) return;
    await saveTabs(open, clientId);
  }

  async function exportData() {
    const clients = (await backend.getAll("clients")).sort(
      (a, b) => a.created - b.created || (a.id < b.id ? -1 : 1),
    );
    return { clients, notes: sortNotes(await backend.getAll("notes")) };
  }

  function validate({ clients, notes }) {
    if (!Array.isArray(clients) || !Array.isArray(notes)) throw new Error("neveljavni podatki");
    const ids = new Set();
    for (const c of clients) {
      if (typeof c?.id !== "string" || typeof c?.name !== "string" || !c.name.trim())
        throw new Error("neveljavna stranka");
      ids.add(c.id);
    }
    for (const n of notes) {
      if (
        typeof n?.id !== "string" ||
        !ids.has(n.clientId) ||
        typeof n.date !== "string" ||
        typeof n.text !== "string"
      ) {
        throw new Error("neveljaven zapis");
      }
    }
  }

  // Zamenja vse; ključ varnostne kopije (meta) ostane, zavihki in trenutni zapisi pa se ponastavijo
  // na tiste, ki še obstajajo.
  async function importData(data) {
    validate(data);
    const ids = new Set(data.clients.map((c) => c.id));
    const kept = (await backend.getAll("meta")).filter(
      (m) => m.key !== TABS_KEY && !m.key.startsWith(CURRENT_PREFIX),
    );
    const saved = await backend.get("meta", TABS_KEY);
    const open = (saved?.open || []).filter((id) => ids.has(id));
    const meta = [
      ...kept,
      { key: TABS_KEY, open, active: open.includes(saved?.active) ? saved.active : null },
    ];
    // Samo znana polja: uvožena datoteka ne vnese tujih ključev (npr. `__proto__`) v zapise.
    const created = (v) => (Number.isFinite(v) ? v : 0);
    await backend.replaceAll({
      clients: data.clients.map((c) => ({ id: c.id, name: c.name, created: created(c.created) })),
      notes: data.notes.map((n) => ({
        id: n.id,
        clientId: n.clientId,
        date: n.date,
        created: created(n.created),
        text: n.text,
      })),
      meta,
    });
  }

  return {
    addClient,
    renameClient,
    deleteClient,
    deleteNote,
    listClients,
    addNote,
    draftNote,
    commitNote,
    updateNoteText,
    listNotes,
    currentNote,
    setCurrentNote,
    getTabs,
    openTab,
    closeTab,
    setActiveTab,
    exportData,
    importData,
    backend,
  };
}
