import { sortNotes } from "../domain/notes.js";
// Pogled zapisov ene stranke: trenutni zapis v urejevalniku z barvanjem markdowna in kretnja L
// (gesture/planPeek.js, kopija iz LibrePT) za prejšnji/naslednji/nov zapis iste stranke.
//
// Blanket in obe spodnji plasti so ustvarjeni enkrat in samo prestavljeni v pogled: initPlanPeek
// obesi poslušalce na window in jih ne odstrani, zato bi nov blanket ob vsakem izrisu puščal stare.
// Kretnja ne sme čakati na IndexedDB: onOpen izriše iz pomnilnika v istem opravilu (sicer bi se
// najprej pokazal star zapis, ki se vrača na mesto), shranjuje pa pozneje.
import { initPlanPeek } from "../gesture/planPeek.js";
import { el } from "./dom.js";
import { highlightBlock, paintHighlight } from "./highlight.js";

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

// Zapis, ki ga brišemo, ne sme več dobiti shranjevanja iz čakalne vrste.
function discardPendingSave() {
  if (pending) clearTimeout(pending.timer);
  pending = null;
}

function queueSave(store, id, text) {
  if (pending) clearTimeout(pending.timer);
  pending = { store, id, text, timer: setTimeout(flushPendingSave, SAVE_DELAY_MS) };
}

addEventListener("pagehide", flushPendingSave);
document.addEventListener(
  "visibilitychange",
  () => document.visibilityState === "hidden" && flushPendingSave(),
);

// Stanje pogleda: kar kretnja potrebuje sinhrono.
const view = { t: null, store: null, client: null, notes: [], currentId: null, show: null };
let host = null;

function underLayer(side) {
  return el("div", {
    cls: `plan-peek-under plan-peek-under-${side}`,
    attrs: { id: `note-peek-${side}` },
  });
}

function getHost() {
  if (host) return host;
  const blanket = el("div", { cls: "plan-peek-blanket", attrs: { id: "note-blanket" } });
  const past = underLayer("past");
  const future = underLayer("future");
  // Gumb za brisanje je zunaj blanketa: pritisk nanj ne začne kretnje L.
  const toolbar = el(
    "div",
    { cls: "note-toolbar" },
    el("span", { cls: "note-hint", text: view.t("noteHint") }),
    el("button", {
      cls: "delete-note danger",
      text: view.t("deleteNote"),
      attrs: { type: "button" },
      on: { click: deleteCurrent },
    }),
  );
  host = {
    root: el(
      "div",
      { cls: "note-page" },
      toolbar,
      el("div", { cls: "peek-host" }, blanket, past, future),
    ),
    blanket,
    past,
    future,
  };
  initPlanPeek(blanket, {
    getUnderLayers: () => ({ past: host.past, future: host.future }),
    isDisabled: () => false,
    onPeekBegin: () => {},
    onOpen: openSide,
  });
  return host;
}

async function deleteCurrent() {
  const note = view.notes[currentIndex()];
  if (!note || !confirm(view.t("deleteNoteConfirm").replace("{date}", note.date))) return;
  discardPendingSave();
  await view.store.deleteNote(note.id);
  view.show();
}

function currentIndex() {
  return view.notes.findIndex((n) => n.id === view.currentId);
}

function openSide(side) {
  const index = currentIndex();
  const target = view.notes[index + (side === "past" ? -1 : 1)];
  if (target) {
    view.currentId = target.id;
    paint();
    view.store.setCurrentNote(view.client.id, target.id);
    return;
  }
  if (side !== "future") return;
  // Najnovejši zapis: L odpre novega s trenutnim datumom.
  const note = view.store.draftNote(view.client.id);
  view.notes = sortNotes([...view.notes, note]);
  view.currentId = note.id;
  paint({ focus: true });
  view.store.commitNote(note);
}

function buildEditor(note) {
  const pre = el("pre", { cls: "md-highlight", attrs: { "aria-hidden": "true" } });
  const input = el("textarea", {
    cls: "md-input",
    attrs: { "aria-label": view.t("noteLabel"), spellcheck: "false", autocapitalize: "sentences" },
  });
  input.value = note.text;
  paintHighlight(pre, note.text);
  input.addEventListener("input", () => {
    note.text = input.value; // v pomnilniku, da spodnji plasti pokažeta sveže besedilo
    paintHighlight(pre, input.value);
    queueSave(view.store, note.id, input.value);
  });
  return { wrap: el("div", { cls: "md-wrap" }, pre, input), input };
}

function underLabel(rest, open) {
  return el(
    "div",
    { cls: "plan-peek-under-label" },
    el("span", { cls: "plan-peek-label-rest", text: rest }),
    el("span", { cls: "plan-peek-label-open", text: open }),
  );
}

// Spodnja plast: sosednji zapis (razred has-plan), kartica »Nov zapis« (has-create-card) ali prazno.
function paintUnder(layer, side, note) {
  const { t, client } = view;
  layer.classList.remove("has-plan", "has-create-card", "is-open-ready", "is-side-chosen");
  layer.scrollTop = 0;
  if (note) {
    layer.classList.add("has-plan");
    layer.replaceChildren(
      el(
        "div",
        { cls: "plan-peek-under-head" },
        el("strong", { cls: "plan-peek-under-title", text: note.date }),
        el("span", { cls: "plan-peek-under-meta", text: client.name }),
      ),
      underLabel(
        `${t(side === "past" ? "peekPrevious" : "peekNext")} · ${note.date}`,
        t("peekUpOpen"),
      ),
      highlightBlock(note.text || t("emptyNote")),
    );
  } else if (side === "future") {
    layer.classList.add("has-create-card");
    layer.replaceChildren(
      underLabel(t("peekNext"), t("peekUpCreate")),
      el(
        "div",
        { cls: "plan-peek-create-card" },
        el("strong", { text: t("peekNoNext") }),
        el("span", { cls: "plan-peek-create-cell", text: t("peekCreateCard") }),
      ),
    );
  } else {
    layer.replaceChildren(el("p", { cls: "plan-peek-under-empty", text: t("peekNoPrevious") }));
  }
}

function paint({ focus = false } = {}) {
  const { blanket, past, future } = getHost();
  const index = currentIndex();
  const note = view.notes[index];
  const { wrap, input } = buildEditor(note);
  blanket.replaceChildren(
    el(
      "div",
      { cls: "note-head" },
      el("span", { cls: "note-date", text: note.date }),
      el("span", { cls: "note-count", text: `${index + 1} / ${view.notes.length}` }),
    ),
    el("div", { cls: "note-body" }, wrap),
  );
  paintUnder(past, "past", view.notes[index - 1]);
  paintUnder(future, "future", view.notes[index + 1]);
  if (focus) input.focus();
}

/** Izriše trenutni zapis stranke ali prazno stanje; `show` ponovno izriše pogled. */
export async function renderNoteView(root, { t, store, client, show }) {
  await flushPendingSave();
  const notes = await store.listNotes(client.id);
  const note = await store.currentNote(client.id);
  Object.assign(view, { t, store, client, notes, currentId: note?.id ?? null, show });
  if (!note) {
    root.replaceChildren(
      el(
        "div",
        { cls: "note-empty" },
        el("p", { text: t("noNotes") }),
        el("button", {
          cls: "primary",
          text: t("newNote"),
          attrs: { type: "button" },
          on: {
            click: async () => {
              await store.addNote(client.id);
              show();
            },
          },
        }),
      ),
    );
    return;
  }
  paint();
  root.replaceChildren(getHost().root);
}
