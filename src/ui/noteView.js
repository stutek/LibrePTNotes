import { parseDateTime } from "../domain/dates.js";
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

// Kratek zamik: zaprtje ali osvežitev strani takoj po tipkanju ne počaka na asinhroni zapis v
// IndexedDB, zato je okno za izgubo besedila toliko krajše (raziskovalno testiranje: do ~0,4 s).
const SAVE_DELAY_MS = 200;

// Neuspešen zapis (brskalnik je zaprl ali izbrisal bazo) mora biti viden: tipkanje sicer izgleda
// shranjeno, po osvežitvi pa je vse izgubljeno. `report(napaka)` ob uspehu dobi null.
let report = () => {};
export function onSaveResult(handler) {
  report = handler;
}
// Vrne true, če je zapis uspel.
const guarded = (promise) =>
  promise.then(
    () => {
      report(null);
      return true;
    },
    (error) => {
      report(error);
      return false;
    },
  );

// Isti zapis v dveh zavihkih brskalnika: zadnji bi tiho pisal čez prvega. Zavihek, ki zapis shrani,
// to sporoči ostalim; tisti, ki ima isti zapis odprt, opozori. (Ime kanala nosi predpono libreptnotes-,
// ker je izvor skupen z LibrePT.)
const channel =
  typeof BroadcastChannel === "function" ? new BroadcastChannel("libreptnotes-notes") : null;
let onForeign = () => {};
export function onForeignEdit(handler) {
  onForeign = handler;
}
channel?.addEventListener("message", (event) => {
  if (event.data?.noteId && event.data.noteId === view.currentId) onForeign();
});

// Neshranjeno besedilo; izplakne se pred menjavo zapisa, ob skritju strani in ob zaprtju.
let pending = null; // { store, id, text, timer }

export async function flushPendingSave() {
  if (!pending) return;
  const { store, id, text, timer } = pending;
  pending = null;
  clearTimeout(timer);
  if (await guarded(store.updateNoteText(id, text))) channel?.postMessage({ noteId: id });
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
let focusAfterRender = false;

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
  if (!note) return;
  // Datum sam ne pove, kateri zapis gre: pokaži tudi začetek besedila.
  const preview =
    [...note.text.replace(/\s+/g, " ").trim()].slice(0, 40).join("") || view.t("emptyNote");
  const question = view
    .t("deleteNoteConfirm")
    .replace("{date}", note.date)
    .replace("{preview}", preview);
  if (!confirm(question)) return;
  discardPendingSave();
  await view.store.deleteNote(note.id);
  view.show();
}

function currentIndex() {
  return view.notes.findIndex((n) => n.id === view.currentId);
}

function openSide(side) {
  endDateEdit({ apply: true });
  const index = currentIndex();
  const target = view.notes[index + (side === "past" ? -1 : 1)];
  if (target) {
    view.currentId = target.id;
    paint();
    guarded(view.store.setCurrentNote(view.client.id, target.id));
    return;
  }
  if (side !== "future") return;
  // Najnovejši zapis: L odpre novega s trenutnim datumom.
  const note = view.store.draftNote(view.client.id);
  view.notes = sortNotes([...view.notes, note]);
  view.currentId = note.id;
  paint({ focus: true });
  guarded(view.store.commitNote(note));
}

function buildEditor(note) {
  const pre = el("pre", { cls: "md-highlight", attrs: { "aria-hidden": "true" } });
  const input = el("textarea", {
    cls: "md-input",
    attrs: {
      "aria-label": view.t("noteLabel"),
      placeholder: view.t("notePlaceholder"),
      spellcheck: "false",
      autocapitalize: "sentences",
    },
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

// Dotik datuma ga zamenja z besedilnim poljem `YYYY-MM-DD HH:MM` (ne datetime-local: telefon bi v njem
// pokazal uro po svojih nastavitvah). Veljaven vnos preuredi zapise in se shrani; neveljaven ostane v
// polju z razlogom, Escape ga zavrže.
let dateEdit = null; // odprto polje: { note, field, finished }

function applyDate(note, date) {
  if (date === note.date) return;
  note.date = date;
  view.notes = sortNotes(view.notes);
  // Neshranjeno besedilo najprej: oba zapisa bereta in pišeta isto vrstico.
  flushPendingSave().then(() => guarded(view.store.updateNoteDate(note.id, date)));
}

// Zapre odprto polje, preden karkoli zamenja ali odstrani njegov DOM (kretnja, menjava zapisa ali
// zavihka). Brez tega polje ob odstranitvi sproži `blur` sredi `replaceChildren`, ki se zato prekine
// in nov zapis ni nikoli shranjen. `apply`: veljaven vnos se obdrži, neveljaven se zavrže.
function endDateEdit({ apply }) {
  const edit = dateEdit;
  if (!edit) return;
  dateEdit = null;
  edit.finished = true;
  const date = apply ? parseDateTime(edit.field.value) : null;
  if (date) applyDate(edit.note, date);
}

function editDate(head, dateButton, note) {
  const { t } = view;
  endDateEdit({ apply: true });
  const field = el("input", {
    cls: "note-date-input",
    attrs: {
      type: "text",
      inputmode: "numeric",
      maxlength: "16",
      autocomplete: "off",
      "aria-label": t("dateEditLabel"),
    },
  });
  field.value = note.date;
  const error = el("span", { cls: "note-date-error", attrs: { role: "alert" } });
  error.hidden = true;
  const edit = { note, field, finished: false };
  dateEdit = edit;
  function commit() {
    const date = parseDateTime(field.value);
    if (!date) {
      field.classList.add("is-invalid");
      field.setAttribute("aria-invalid", "true");
      error.textContent = t("dateInvalid");
      error.hidden = false;
      return false;
    }
    endDateEdit({ apply: true });
    paint();
    return true;
  }
  field.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      commit();
    } else if (e.key === "Escape") {
      endDateEdit({ apply: false });
      paint();
    }
  });
  // Umik s polja: veljaven vnos se shrani, neveljaven se zavrže (telefon nima Escape).
  field.addEventListener("blur", () => {
    if (edit.finished) return;
    if (!commit()) {
      endDateEdit({ apply: false });
      paint();
    }
  });
  dateButton.replaceWith(field);
  head.append(error);
  field.focus();
  field.select();
}

function paint({ focus = false } = {}) {
  endDateEdit({ apply: false });
  const { blanket, past, future } = getHost();
  const index = currentIndex();
  const note = view.notes[index];
  const { wrap, input } = buildEditor(note);
  const head = el("div", { cls: "note-head" });
  const dateButton = el("button", {
    cls: "note-date",
    text: note.date,
    attrs: { type: "button", "aria-label": `${view.t("dateEditLabel")}: ${note.date}` },
    on: { click: () => editDate(head, dateButton, note) },
  });
  head.append(
    dateButton,
    el("span", { cls: "note-count", text: `${index + 1} / ${view.notes.length}` }),
  );
  blanket.replaceChildren(head, el("div", { cls: "note-body" }, wrap));
  paintUnder(past, "past", view.notes[index - 1]);
  paintUnder(future, "future", view.notes[index + 1]);
  if (focus) input.focus();
}

/** Izriše trenutni zapis stranke ali prazno stanje; `show` ponovno izriše pogled. */
export async function renderNoteView(root, { t, store, client, show }) {
  endDateEdit({ apply: true });
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
              focusAfterRender = true; // prazen zapis je namenjen pisanju: tipkovnica naj se odpre
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
  // Fokus šele, ko je pogled v dokumentu: element zunaj dokumenta se ne da fokusirati.
  // Z miško ali tipkovnico je urejevalnik takoj pripravljen; na dotik se tipkovnica ne odpre sama
  // (trener zapis najprej bere), razen po gumbu »Nov zapis«.
  if (focusAfterRender || matchMedia("(hover: hover) and (pointer: fine)").matches) {
    root.querySelector(".plan-peek-blanket .md-input")?.focus();
  }
  focusAfterRender = false;
}
