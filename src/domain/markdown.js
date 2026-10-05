// Barvanje markdowna: besedilo se ne spremeni, samo razdeli na odseke z razredom. Zato združeni odseki
// vedno dajo vhod, kar omogoča prosojen textarea nad barvanim pre (poravnava je znak za znakom).
const INLINE = new RegExp(
  [
    "(`[^`\\n]+`)", // 1 koda
    "(\\*\\*[^*\\n]+\\*\\*|__[^_\\n]+__)", // 2 krepko
    "(\\*[^*\\s][^*\\n]*?\\*|(?<![\\w])_[^_\\s][^_\\n]*?_(?![\\w]))", // 3 ležeče
    "(\\[[^\\]\\n]+\\]\\([^)\\s]*\\))", // 4 povezava
  ].join("|"),
  "g",
);
const INLINE_CLASSES = [null, "md-code", "md-bold", "md-italic", "md-link"];

const FENCE = /^\s*(```|~~~)/;
const HEADING = /^#{1,6}(\s|$)/;
const QUOTE = /^\s*>/;
const LIST = /^(\s*)([-*+]|\d+[.)])(?=\s)/;

function inline(text, out) {
  let last = 0;
  for (const m of text.matchAll(INLINE)) {
    if (m.index > last) out.push({ text: text.slice(last, m.index), cls: null });
    out.push({ text: m[0], cls: INLINE_CLASSES[m.slice(1).findIndex((g) => g !== undefined) + 1] });
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push({ text: text.slice(last), cls: null });
}

function line(text, state, out) {
  if (FENCE.test(text)) {
    state.fenced = !state.fenced;
    out.push({ text, cls: "md-fence" });
  } else if (state.fenced) out.push({ text, cls: "md-code" });
  else if (HEADING.test(text)) out.push({ text, cls: "md-heading" });
  else if (QUOTE.test(text)) out.push({ text, cls: "md-quote" });
  else {
    const list = LIST.exec(text);
    if (list) {
      if (list[1]) out.push({ text: list[1], cls: null });
      out.push({ text: list[2], cls: "md-marker" });
      inline(text.slice(list[0].length), out);
    } else inline(text, out);
  }
}

/** Razdeli besedilo na odseke `{text, cls}`; `cls` je null za navadno besedilo. */
export function tokenize(text) {
  const out = [];
  const state = { fenced: false };
  const lines = text.split("\n");
  lines.forEach((l, i) => {
    line(l, state, out);
    if (i < lines.length - 1) out.push({ text: "\n", cls: null });
  });
  // Sosednji odseki z enakim razredom v enega, brez praznih.
  return out.reduce((acc, seg) => {
    if (!seg.text) return acc;
    const prev = acc[acc.length - 1];
    if (prev && prev.cls === seg.cls) prev.text += seg.text;
    else acc.push({ ...seg });
    return acc;
  }, []);
}
