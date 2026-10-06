import assert from "node:assert/strict";
import { test } from "node:test";
import { formatBuildInfo } from "../../../src/domain/buildInfo.js";
import { formatDateTime } from "../../../src/domain/dates.js";
import { BUILD_INFO } from "../../../src/version.js";

test("žig gradnje: commit in čas gradnje v krajevnem času v 24-urni ISO obliki", () => {
  const local = formatDateTime(new Date("2026-10-05T14:30Z"));
  assert.equal(
    formatBuildInfo({ commit: "abc1234", builtAt: "2026-10-05T14:30Z" }),
    `abc1234 · ${local}`,
  );
  assert.match(local, /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/, "brez UTC pripone in brez 12-urne ure");
});

test("razvojni žig je samo »dev«", () => {
  assert.equal(formatBuildInfo({ commit: "dev", builtAt: "" }), "dev");
});

test("shranjena kopija version.js je razvojna (gradnja jo prepiše)", () => {
  assert.deepEqual(BUILD_INFO, { commit: "dev", builtAt: "" });
});
