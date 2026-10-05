import assert from "node:assert/strict";
import { test } from "node:test";
import { formatBuildInfo } from "../../../src/domain/buildInfo.js";
import { BUILD_INFO } from "../../../src/version.js";

test("žig gradnje: commit in čas UTC v 24-urni ISO obliki", () => {
  assert.equal(
    formatBuildInfo({ commit: "abc1234", builtAt: "2026-10-05T14:30Z" }),
    "abc1234 · 2026-10-05 14:30 UTC",
  );
});

test("razvojni žig je samo »dev«", () => {
  assert.equal(formatBuildInfo({ commit: "dev", builtAt: "" }), "dev");
});

test("shranjena kopija version.js je razvojna (gradnja jo prepiše)", () => {
  assert.deepEqual(BUILD_INFO, { commit: "dev", builtAt: "" });
});
