import { test } from "node:test";
import assert from "node:assert/strict";
import { createStore } from "../src/data/store.js";
import { memoryBackend } from "./memoryBackend.js";

function make(start = new Date(2026, 9, 5, 9, 0)) {
  let clock = start.getTime();
  let seq = 0;
  const store = createStore(memoryBackend(), {
    now: () => new Date(clock),
    newId: () => `id${++seq}`,
  });
  return { store, tick: (min = 1) => (clock += min * 60000) };
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
  assert.deepEqual((await store.listClients()).map((c) => c.name), ["Ana", "Čoh", "Žan"]);
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
  assert.deepEqual((await store.listNotes(a.id)).map((x) => x.id), [first.id, second.id]);
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
  await assert.rejects(() => store.importData({ clients: [{ id: "x", name: "X" }], notes: [{ id: "n", clientId: "zlo", date: "d", text: "" }] }));
  assert.equal((await store.listClients()).length, 1);
});
