import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { join, relative } from "node:path";

const SRC = new URL("../src/", import.meta.url).pathname;

function files(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? files(join(dir, e.name)) : [join(dir, e.name)],
  );
}

test("service worker predpomni vsako datoteko iz src/ (razen sebe)", () => {
  const sw = readFileSync(join(SRC, "sw.js"), "utf8");
  const listed = [...sw.matchAll(/"\.\/([^"]*)"/g)].map((m) => m[1]);
  const actual = files(SRC).map((f) => relative(SRC, f)).filter((f) => f !== "sw.js");
  for (const f of actual) assert.ok(listed.includes(f), `manjka v PRECACHE: ${f}`);
});

test("imena predpomnilnika in poti ne trčijo z LibrePT", () => {
  const sw = readFileSync(join(SRC, "sw.js"), "utf8");
  assert.match(sw, /const CACHE = "libreptnotes-v\d+"/);
  assert.doesNotMatch(sw, /"\/[^"]*"/, "poti morajo biti relativne");
});

test("manifest ima relativne poti in svoje ime", () => {
  const m = JSON.parse(readFileSync(join(SRC, "manifest.webmanifest"), "utf8"));
  assert.equal(m.name, "LibrePTNotes");
  assert.equal(m.start_url, "./");
  assert.equal(m.scope, "./");
  for (const icon of m.icons) assert.ok(icon.src.startsWith("./"));
});
