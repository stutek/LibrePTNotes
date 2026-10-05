import assert from "node:assert/strict";
import { test } from "node:test";
import { formatDateTime } from "../../../src/domain/dates.js";

test("datum je ISO z 24-urno uro in vodilnimi ničlami", () => {
  assert.equal(formatDateTime(new Date(2026, 0, 5, 7, 3)), "2026-01-05 07:03");
  assert.equal(formatDateTime(new Date(2026, 9, 5, 23, 59)), "2026-10-05 23:59");
  assert.equal(formatDateTime(new Date(2026, 9, 5, 0, 0)), "2026-10-05 00:00");
});
