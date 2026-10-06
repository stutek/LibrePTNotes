import assert from "node:assert/strict";
import { test } from "node:test";
import { clientToMarkdown, noteLabel, safeFileName } from "../../../src/domain/exportText.js";

const client = { id: "c1", name: "Ana Novak" };
const notes = [
  { id: "n1", clientId: "c1", date: "2026-10-01 18:00", title: "", text: "# Prvi\nčučanje" },
  { id: "n2", clientId: "c1", date: "2026-10-02 18:00", title: "Načrt tedna", text: "- A\n- B" },
];

test("izvoz stranke je berljiv markdown: ime, datum izvoza, zapisi z naslovom in datumom", () => {
  const text = clientToMarkdown(client, notes, { exportedAt: "2026-10-06 21:00" });
  assert.match(text, /^# Ana Novak\n/);
  assert.match(text, /Izvoz: 2026-10-06 21:00/);
  assert.match(text, /## 2026-10-01 18:00\n/, "brez naslova je naslov datum");
  assert.match(text, /## Načrt tedna\n\n\*2026-10-02 18:00\*/, "naslov, nato datum");
  assert.ok(text.includes("# Prvi\nčučanje"));
  assert.ok(text.indexOf("2026-10-01") < text.indexOf("Načrt tedna"), "najstarejši najprej");
});

test("stranka brez zapisov se izvozi brez napake", () => {
  assert.match(clientToMarkdown(client, [], { exportedAt: "2026-10-06 21:00" }), /Ni zapisov/);
});

test("oznaka zapisa: naslov, sicer prva vrstica, sicer datum", () => {
  assert.equal(noteLabel({ title: "Načrt", text: "x", date: "d" }), "Načrt");
  assert.equal(noteLabel({ title: "  ", text: "\n# Dan 1\nrest", date: "d" }), "Dan 1");
  assert.equal(noteLabel({ title: "", text: "", date: "2026-10-01 18:00" }), "2026-10-01 18:00");
  assert.equal(noteLabel({ title: "", text: "a".repeat(100), date: "d" }).length <= 41, true);
});

test("ime datoteke ne vsebuje poti ali posebnih znakov", () => {
  assert.equal(safeFileName("Ana Novak"), "Ana-Novak");
  assert.equal(safeFileName("../../etc/passwd"), "etc-passwd");
  assert.equal(safeFileName("Čoh/Žan <3"), "Čoh-Žan-3");
  assert.equal(safeFileName("   "), "stranka");
});
