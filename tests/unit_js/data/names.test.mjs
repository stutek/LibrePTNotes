import assert from "node:assert/strict";
import { test } from "node:test";
import { DB_NAME } from "../../../src/data/idbBackend.js";

test("baza je libreptnotes (skupna domena z LibrePT)", () => {
  assert.equal(DB_NAME, "libreptnotes");
});
