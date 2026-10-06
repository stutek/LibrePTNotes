import assert from "node:assert/strict";
import { test } from "node:test";
import { initialOf } from "../../../src/domain/names.js";

test("začetnica je prvi znak, ki ga uporabnik vidi, z velikostjo črke", () => {
  assert.equal(initialOf("Ana"), "A");
  assert.equal(initialOf("čoh"), "Č");
  assert.equal(initialOf("  žan"), "Ž");
});

test("zastava in družinski emoji se ne razpolovita", () => {
  assert.equal(initialOf("🇸🇮 Slovenija"), "🇸🇮");
  assert.equal(initialOf("👨‍👩‍👧 Družina"), "👨‍👩‍👧");
  assert.equal(initialOf("👍🏽 ok"), "👍🏽");
});

test("prazno ime da prazen niz", () => {
  assert.equal(initialOf(""), "");
  assert.equal(initialOf("   "), "");
});
