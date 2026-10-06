import assert from "node:assert/strict";
import { test } from "node:test";
import { createStore } from "../../../src/data/store.js";
import { memoryBackend } from "../helpers/memoryBackend.mjs";

function make(start = new Date(2026, 9, 5, 9, 0)) {
  let clock = start.getTime();
  let seq = 0;
  const store = createStore(memoryBackend(), {
    now: () => new Date(clock),
    newId: () => `id${++seq}`,
  });
  return {
    store,
    tick: (min = 1) => {
      clock += min * 60000;
    },
  };
}

test("stranka: ime se obreže, prazno ime se zavrne", async () => {
  const { store } = make();
  const c = await store.addClient("  Ana Novak ");
  assert.equal(c.name, "Ana Novak");
  await assert.rejects(() => store.addClient("   "));
});

test("seznam strank je po imenu (slovenska abeceda)", async () => {
  const { store } = make();
  await store.addClient("Žan");
  await store.addClient("Ana");
  await store.addClient("Čoh");
  assert.deepEqual(
    (await store.listClients()).map((c) => c.name),
    ["Ana", "Čoh", "Žan"],
  );
});

test("zapis dobi datum ob ustvarjanju v obliki YYYY-MM-DD HH:MM", async () => {
  const { store } = make();
  const c = await store.addClient("Ana");
  const note = await store.addNote(c.id);
  assert.equal(note.date, "2026-10-05 09:00");
  assert.equal(note.text, "");
});

test("besedilo se posodobi, datum ostane", async () => {
  const { store, tick } = make();
  const c = await store.addClient("Ana");
  const note = await store.addNote(c.id);
  tick(30);
  await store.updateNoteText(note.id, "# Dan 1");
  const [saved] = await store.listNotes(c.id);
  assert.equal(saved.text, "# Dan 1");
  assert.equal(saved.date, "2026-10-05 09:00");
});

test("zapisi so ločeni po strankah in urejeni po datumu", async () => {
  const { store, tick } = make();
  const a = await store.addClient("Ana");
  const b = await store.addClient("Bor");
  const first = await store.addNote(a.id, "prvi");
  tick(10);
  await store.addNote(b.id, "tuj");
  tick(10);
  const second = await store.addNote(a.id, "drugi");
  assert.deepEqual(
    (await store.listNotes(a.id)).map((x) => x.id),
    [first.id, second.id],
  );
  assert.equal((await store.listNotes(b.id)).length, 1);
});

test("zavihki: odpri, ne podvajaj, zapri; aktiven samo odprt", async () => {
  const { store } = make();
  const a = await store.addClient("Ana");
  const b = await store.addClient("Bor");
  assert.deepEqual(await store.getTabs(), { open: [], active: null });
  await store.openTab(a.id);
  await store.openTab(b.id);
  await store.openTab(a.id);
  assert.deepEqual(await store.getTabs(), { open: [a.id, b.id], active: a.id });
  await store.setActiveTab(b.id);
  assert.equal((await store.getTabs()).active, b.id);
  await store.setActiveTab("neznan");
  assert.equal((await store.getTabs()).active, b.id, "neodprt zavihek se ne izbere");
  await store.closeTab(b.id);
  assert.deepEqual(await store.getTabs(), { open: [a.id], active: null });
  await store.setActiveTab(null);
  assert.equal((await store.getTabs()).active, null);
});

test("odprti zavihki ostanejo po ponovnem nalaganju (ista baza, nov store)", async () => {
  const backend = memoryBackend();
  const first = createStore(backend, { newId: () => "c1" });
  const c = await first.addClient("Ana");
  await first.openTab(c.id);
  const reloaded = createStore(backend);
  assert.deepEqual(await reloaded.getTabs(), { open: ["c1"], active: "c1" });
});

test("trenutni zapis stranke se zapomni; privzeto najnovejši", async () => {
  const { store, tick } = make();
  const c = await store.addClient("Ana");
  assert.equal(await store.currentNote(c.id), null);
  const first = await store.addNote(c.id, "a");
  tick();
  const second = await store.addNote(c.id, "b");
  assert.equal((await store.currentNote(c.id)).id, second.id, "po novem zapisu je trenutni ta");
  await store.setCurrentNote(c.id, first.id);
  assert.equal((await store.currentNote(c.id)).id, first.id);
});

test("izvoz in uvoz zamenjata vse; zavihki neobstoječih strank odpadejo", async () => {
  const { store } = make();
  const a = await store.addClient("Ana");
  await store.addNote(a.id, "stari");
  await store.openTab(a.id);
  const data = {
    clients: [{ id: "x", name: "Xena", created: 1 }],
    notes: [{ id: "n", clientId: "x", date: "2026-01-01 08:00", created: 1, text: "novi" }],
  };
  await store.importData(data);
  assert.deepEqual(await store.exportData(), data);
  assert.deepEqual(await store.getTabs(), { open: [], active: null });
  assert.equal((await store.currentNote("x")).id, "n");
});

test("uvoz zavrne napačno obliko in ne spremeni baze", async () => {
  const { store } = make();
  await store.addClient("Ana");
  await assert.rejects(() => store.importData({ clients: "ne", notes: [] }));
  await assert.rejects(() =>
    store.importData({
      clients: [{ id: "x", name: "X" }],
      notes: [{ id: "n", clientId: "zlo", date: "d", text: "" }],
    }),
  );
  assert.equal((await store.listClients()).length, 1);
});

test("draftNote ne shrani, commitNote shrani in nastavi trenutni zapis", async () => {
  const { store } = make();
  const c = await store.addClient("Ana");
  const draft = store.draftNote(c.id, "t");
  assert.equal((await store.listNotes(c.id)).length, 0);
  assert.equal(draft.date, "2026-10-05 09:00");
  await store.commitNote(draft);
  assert.equal((await store.currentNote(c.id)).id, draft.id);
});

test("preimenovanje stranke: ime se obreže, prazno in neznana stranka se zavrneta", async () => {
  const { store } = make();
  const c = await store.addClient("Ana");
  await store.renameClient(c.id, "  Anja ");
  assert.deepEqual(
    (await store.listClients()).map((x) => x.name),
    ["Anja"],
  );
  await assert.rejects(() => store.renameClient(c.id, "  "));
  await assert.rejects(() => store.renameClient("ni", "X"));
});

test("brisanje stranke zbriše njene zapise, zavihek in trenutni zapis, drugih ne", async () => {
  const { store } = make();
  const ana = await store.addClient("Ana");
  const bor = await store.addClient("Bor");
  await store.addNote(ana.id, "a");
  await store.addNote(bor.id, "b");
  await store.openTab(ana.id);
  await store.openTab(bor.id);
  await store.deleteClient(ana.id);
  assert.deepEqual(
    (await store.listClients()).map((c) => c.id),
    [bor.id],
  );
  assert.equal((await store.backend.getAll("notes")).length, 1);
  assert.equal(await store.backend.get("meta", `current:${ana.id}`), undefined);
  assert.deepEqual(await store.getTabs(), { open: [bor.id], active: bor.id });
});

test("brisanje zapisa: trenutni preide na prejšnjega, najstarejši na naslednjega, zadnji v prazno", async () => {
  const { store, tick } = make();
  const c = await store.addClient("Ana");
  const ids = [];
  for (const text of ["1", "2", "3"]) {
    ids.push((await store.addNote(c.id, text)).id);
    tick();
  }
  await store.setCurrentNote(c.id, ids[1]);
  assert.equal(await store.deleteNote(ids[1]), ids[0]);
  assert.equal((await store.currentNote(c.id)).id, ids[0]);
  assert.equal(await store.deleteNote(ids[0]), ids[2]);
  assert.equal(await store.deleteNote(ids[2]), null);
  assert.equal(await store.currentNote(c.id), null);
  assert.equal(await store.backend.get("meta", `current:${c.id}`), undefined);
});

test("brisanje zapisa, ki ni trenutni, trenutnega ne premakne", async () => {
  const { store, tick } = make();
  const c = await store.addClient("Ana");
  const a = await store.addNote(c.id, "1");
  tick();
  const b = await store.addNote(c.id, "2");
  assert.equal(await store.deleteNote(a.id), b.id);
  assert.equal((await store.currentNote(c.id)).id, b.id);
  await assert.rejects(() => store.deleteNote("ni"));
});

test("listNotes bere zapise prek indeksa clientId, ne vseh zapisov", async () => {
  const calls = [];
  const inner = (await import("../helpers/memoryBackend.mjs")).memoryBackend();
  const backend = {
    ...inner,
    async getAll(name) {
      calls.push(["getAll", name]);
      return inner.getAll(name);
    },
    async getAllByIndex(name, index, key) {
      calls.push(["getAllByIndex", name, index, key]);
      return inner.getAllByIndex(name, index, key);
    },
  };
  const store = createStore(backend, {
    newId: (() => {
      let i = 0;
      return () => `i${++i}`;
    })(),
  });
  const a = await store.addClient("Ana");
  const b = await store.addClient("Bor");
  await store.addNote(a.id, "a");
  await store.addNote(b.id, "b");
  calls.length = 0;
  const notes = await store.listNotes(a.id);
  assert.deepEqual(
    notes.map((n) => n.text),
    ["a"],
  );
  // is the contract: the requirement is that listNotes reads through the clientId index, never every note.
  assert.deepEqual(
    calls,
    [["getAllByIndex", "notes", "clientId", a.id]],
    "brez getAll nad vsemi zapisi",
  );
});
