// src/domain/exportText.js — izvoz zapisov stranke v berljiv markdown, oznaka zapisa, ime datoteke.
// Čista logika brez DOM. Izvoz je namenjen stranki (pravica do vpogleda in prenosljivosti, GDPR) ali
// trenerju za arhiv: je navadno besedilo, zato NI šifriran in ga trener varuje sam.
import { sortNotes } from "./notes.js";

const LABEL_MAX = 40;

/** Kratka oznaka zapisa: naslov, sicer prva neprazna vrstica (brez #), sicer datum. */
export function noteLabel(note) {
  const title = (note.title ?? "").trim();
  if (title) return title;
  const first = (note.text ?? "")
    .split("\n")
    .map((line) => line.replace(/^\s*#{1,6}\s*/, "").trim())
    .find(Boolean);
  if (!first) return note.date;
  return [...first].length > LABEL_MAX ? `${[...first].slice(0, LABEL_MAX).join("")}…` : first;
}

export function clientToMarkdown(client, notes, { exportedAt }) {
  const lines = [`# ${client.name}`, "", `Izvoz: ${exportedAt} (LibrePTNotes)`, ""];
  const sorted = sortNotes(notes);
  if (!sorted.length) lines.push("Ni zapisov.", "");
  for (const note of sorted) {
    const title = (note.title ?? "").trim();
    lines.push(`## ${title || note.date}`, "");
    if (title) lines.push(`*${note.date}*`, "");
    lines.push((note.text ?? "").replace(/\s+$/, ""), "");
  }
  return `${lines
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trimEnd()}\n`;
}

/** Ime datoteke iz imena stranke: brez poti, presledkov in posebnih znakov. */
export function safeFileName(name) {
  const clean = String(name ?? "")
    .normalize("NFC")
    .replace(/[^\p{L}\p{N}]+/gu, "-")
    .replace(/^-+|-+$/g, "");
  return clean || "stranka";
}
