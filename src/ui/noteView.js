// Pogled zapisov ene stranke: trenutni zapis v urejevalniku z barvanjem markdowna.
import { el } from "./dom.js";
import { paintHighlight } from "./highlight.js";

const SAVE_DELAY_MS = 400;

// Neshranjeno besedilo; izplakne se pred menjavo zapisa, ob skritju strani in ob zaprtju.
let pending = null; // { store, id, text, timer }

export async function flushPendingSave() {
  if (!pending) return;
  const { store, id, text, timer } = pending;
  pending = null;
  clearTimeout(timer);
  await store.updateNoteText(id, text);
}

function queueSave(store, id, text) {
  if (pending) clearTimeout(pending.timer);
  pending = { store, id, text, timer: setTimeout(flushPendingSave, SAVE_DELAY_MS) };
}

addEventListener("pagehide", flushPendingSave);
document.addEventListener("visibilitychange", () => document.visibilityState === "hidden" && flushPendingSave());

function buildEditor({ t, store, note }) {
  const pre = el("pre", { cls: "md-highlight", attrs: { "aria-hidden": "true" } });
  const input = el("textarea", {
    cls: "md-input",
    attrs: { "aria-label": t("noteLabel"), spellcheck: "false", autocapitalize: "sentences" },
  });
  input.value = note.text;
  paintHighlight(pre, note.text);
  input.addEventListener("input", () => {
    paintHighlight(pre, input.value);
    queueSave(store, note.id, input.value);
  });
  return el("div", { cls: "md-wrap" }, pre, input);
}

/** Izriše trenutni zapis stranke ali prazno stanje; `show` ponovno izriše pogled. */
export async function renderNoteView(root, { t, store, client, show }) {
  await flushPendingSave();
  const notes = await store.listNotes(client.id);
  const note = await store.currentNote(client.id);
  if (!note) {
    root.replaceChildren(
      el(
        "div",
        { cls: "note-empty" },
        el("p", { text: t("noNotes") }),
        el("button", { cls: "primary", text: t("newNote"), attrs: { type: "button" }, on: { click: async () => { await store.addNote(client.id); show(); } } }),
      ),
    );
    return;
  }
  const index = notes.findIndex((n) => n.id === note.id);
  const head = el(
    "div",
    { cls: "note-head" },
    el("span", { cls: "note-date", text: note.date }),
    el("span", { cls: "note-count", text: `${index + 1} / ${notes.length}` }),
  );
  const body = el("div", { cls: "note-body" }, buildEditor({ t, store, note }));
  root.replaceChildren(el("div", { cls: "peek-host" }, el("div", { id: "note-blanket", cls: "plan-peek-blanket" }, head, body)));
}

