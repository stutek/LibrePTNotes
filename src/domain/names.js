// src/domain/names.js — začetnica imena za avatar.
// Prvi znak, ki ga uporabnik vidi (grafem), ne prvi kodni znak: zastava ali družinski emoji sta več
// kodnih točk in bi se razpolovila.
const SEGMENTER = typeof Intl?.Segmenter === "function" ? new Intl.Segmenter("sl") : null;

export function initialOf(name) {
  const text = String(name ?? "").trim();
  if (!text) return "";
  const first = SEGMENTER
    ? SEGMENTER.segment(text)[Symbol.iterator]().next().value.segment
    : [...text][0];
  return first.toLocaleUpperCase("sl");
}
