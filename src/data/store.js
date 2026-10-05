// Shramba LibrePTNotes: stranke, zapisi, odprti zavihki. Logika je neodvisna od IndexedDB; `backend`
// (idbBackend.js v brskalniku, tests/memoryBackend.js v testih) zna samo getAll/get/put/delete/replaceAll.
// Podatki ostanejo v brskalniku, nič ne gre na strežnik.
import { formatDateTime } from "../domain/dates.js";
import { sortNotes } from "../domain/notes.js";

const TABS_KEY = "tabs";
const CURRENT_PREFIX = "current:";
const COLLATOR = new Intl.Collator("sl");

export function createStore(backend, { now = () => new Date(), newId = () => crypto.randomUUID() } = {}) {
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

  async function setCurrentNote(clientId, noteId) {
    await backend.put("meta", { key: CURRENT_PREFIX + clientId, noteId });
  }

  // Nov zapis je takoj trenutni: kretnja L ga odpre s trenutnim datumom.
  async function addNote(clientId, text = "") {
    const date = now();
    const note = { id: newId(), clientId, date: formatDateTime(date), created: date.getTime(), text };
    await backend.put("notes", note);
    await setCurrentNote(clientId, note.id);
    return note;
  }

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
    await saveTabs(open.filter((id) => id !== clientId), active === clientId ? null : active);
  }

  // null je seznam strank; zavihek, ki ni odprt, se ne izbere.
  async function setActiveTab(clientId) {
    const { open } = await getTabs();
    if (clientId !== null && !open.includes(clientId)) return;
    await saveTabs(open, clientId);
  }

  async function exportData() {
    const clients = (await backend.getAll("clients")).sort((a, b) => (a.created - b.created) || (a.id < b.id ? -1 : 1));
    return { clients, notes: sortNotes(await backend.getAll("notes")) };
  }

  function validate({ clients, notes }) {
    if (!Array.isArray(clients) || !Array.isArray(notes)) throw new Error("neveljavni podatki");
    const ids = new Set();
    for (const c of clients) {
      if (typeof c?.id !== "string" || typeof c?.name !== "string" || !c.name.trim()) throw new Error("neveljavna stranka");
      ids.add(c.id);
    }
    for (const n of notes) {
      if (typeof n?.id !== "string" || !ids.has(n.clientId) || typeof n.date !== "string" || typeof n.text !== "string") {
        throw new Error("neveljaven zapis");
      }
    }
  }

  // Zamenja vse; ključ varnostne kopije (meta) ostane, zavihki in trenutni zapisi pa se ponastavijo
  // na tiste, ki še obstajajo.
  async function importData(data) {
    validate(data);
    const ids = new Set(data.clients.map((c) => c.id));
    const kept = (await backend.getAll("meta")).filter((m) => m.key !== TABS_KEY && !m.key.startsWith(CURRENT_PREFIX));
    const saved = await backend.get("meta", TABS_KEY);
    const open = (saved?.open || []).filter((id) => ids.has(id));
    const meta = [...kept, { key: TABS_KEY, open, active: open.includes(saved?.active) ? saved.active : null }];
    await backend.replaceAll({
      clients: data.clients.map((c) => ({ created: 0, ...c })),
      notes: data.notes.map((n) => ({ created: 0, ...n })),
      meta,
    });
  }

  return { addClient, listClients, addNote, updateNoteText, listNotes, currentNote, setCurrentNote, getTabs, openTab, closeTab, setActiveTab, exportData, importData, backend };
}
