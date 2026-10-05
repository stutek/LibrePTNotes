import { test } from "node:test";
import assert from "node:assert/strict";
import { sortNotes, neighbours } from "../src/domain/notes.js";

const n = (id, date, created = 0) => ({ id, date, created, text: id });

test("zapisi so urejeni po datumu, pri istem datumu po času nastanka", () => {
  const sorted = sortNotes([n("c", "2026-10-02 10:00"), n("b", "2026-10-01 10:00", 2), n("a", "2026-10-01 10:00", 1)]);
  assert.deepEqual(sorted.map((x) => x.id), ["a", "b", "c"]);
});

test("sosedi: prejšnji in naslednji iste stranke", () => {
  const notes = [n("a", "2026-10-01 10:00"), n("b", "2026-10-02 10:00"), n("c", "2026-10-03 10:00")];
  const mid = neighbours(notes, "b");
  assert.equal(mid.previous.id, "a");
  assert.equal(mid.next.id, "c");
  assert.equal(mid.isNewest, false);
  assert.deepEqual([mid.index, mid.total], [1, 3]);
});

test("najnovejši zapis nima naslednjega, najstarejši nima prejšnjega", () => {
  const notes = [n("a", "2026-10-01 10:00"), n("b", "2026-10-02 10:00")];
  assert.equal(neighbours(notes, "b").next, null);
  assert.equal(neighbours(notes, "b").isNewest, true);
  assert.equal(neighbours(notes, "a").previous, null);
});

test("neznan zapis: brez sosedov", () => {
  const r = neighbours([n("a", "2026-10-01 10:00")], "x");
  assert.equal(r.previous, null);
  assert.equal(r.next, null);
  assert.equal(r.index, -1);
});
