import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import { test } from "node:test";
import { generatePassphrase, passphraseProblem } from "../../../src/data/passphraseKey.js";

test("generirano geslo: šest različnih besed in naključen niz, nikoli ponovljena beseda", () => {
  for (let i = 0; i < 500; i += 1) {
    const parts = generatePassphrase(webcrypto).split("-");
    assert.equal(parts.length, 7, "šest besed in niz");
    const words = parts.slice(0, 6);
    assert.equal(new Set(words).size, 6, `ponovljena beseda: ${parts.join("-")}`);
    assert.match(parts[6], /^[a-hj-km-np-z2-9]{8}$/, "niz brez dvoumnih znakov (0, o, 1, l, i)");
  }
});

test("generirana gesla se razlikujejo", () => {
  const seen = new Set(Array.from({ length: 200 }, () => generatePassphrase(webcrypto)));
  assert.equal(seen.size, 200);
});

test("lastno geslo: prekratko se zavrne, kratko opozori, dolgo je v redu", () => {
  assert.equal(passphraseProblem("a"), "short");
  assert.equal(passphraseProblem("1234567"), "short");
  assert.equal(passphraseProblem("12345678"), "weak");
  assert.equal(passphraseProblem("dvanajst-znak"), null);
  assert.equal(passphraseProblem(generatePassphrase(webcrypto)), null);
  assert.equal(passphraseProblem("   a   "), "short", "presledki ne štejejo");
});
