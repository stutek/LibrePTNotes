import assert from "node:assert/strict";
import { test } from "node:test";
import { formatDateTime } from "../../../src/domain/dates.js";

test("datum je ISO z 24-urno uro in vodilnimi ničlami", () => {
  assert.equal(formatDateTime(new Date(2026, 0, 5, 7, 3)), "2026-01-05 07:03");
  assert.equal(formatDateTime(new Date(2026, 9, 5, 23, 59)), "2026-10-05 23:59");
  assert.equal(formatDateTime(new Date(2026, 9, 5, 0, 0)), "2026-10-05 00:00");
});

test("parseDateTime sprejme samo YYYY-MM-DD HH:MM z veljavnim koledarskim datumom", async () => {
  const { parseDateTime } = await import("../../../src/domain/dates.js");
  assert.equal(parseDateTime("2026-10-05 14:30"), "2026-10-05 14:30");
  assert.equal(parseDateTime("  2026-02-28 00:00 "), "2026-02-28 00:00");
  assert.equal(parseDateTime("2028-02-29 23:59"), "2028-02-29 23:59", "prestopno leto");
  for (const bad of [
    "",
    "2026-10-05",
    "2026-10-05T14:30",
    "2026-10-05 2:30 PM",
    "2026-10-05 24:00",
    "2026-10-05 14:60",
    "2026-02-30 10:00",
    "2027-02-29 10:00",
    "2026-13-01 10:00",
    "26-10-05 14:30",
    null,
    undefined,
  ]) {
    assert.equal(parseDateTime(bad), null, String(bad));
  }
});
