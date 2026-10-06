import assert from "node:assert/strict";
import { test } from "node:test";
import { requestDurableStorage } from "../../../src/data/storageDurability.js";

test("zaprosi trajno shrambo, ko je še ni, in pove izid", async () => {
  const granted = { persisted: async () => false, persist: async () => true };
  const denied = { persisted: async () => false, persist: async () => false };
  assert.equal(await requestDurableStorage(granted), "persistent");
  assert.equal(await requestDurableStorage(denied), "best-effort");
});

test("že trajna shramba se ne zaprosi znova", async () => {
  let asked = false;
  const storage = {
    persisted: async () => true,
    persist: async () => {
      asked = true;
      return true;
    },
  };
  assert.equal(await requestDurableStorage(storage), "persistent");
  // avoided side effect: a second persist() prompt would show the user a permission dialog again.
  assert.equal(asked, false);
});

test("brskalnik brez vmesnika ali z napako ne podre aplikacije", async () => {
  assert.equal(await requestDurableStorage(null), "unsupported");
  assert.equal(await requestDurableStorage({}), "unsupported");
  const unreadable = {
    persisted: async () => {
      throw new Error("zavrnjeno");
    },
  };
  // Neberljivo stanje: vseeno prosi; brskalnik, ki odobri, je trajen, ki zavrne ali javi napako, ni.
  assert.equal(
    await requestDurableStorage({ ...unreadable, persist: async () => true }),
    "persistent",
  );
  assert.equal(
    await requestDurableStorage({
      ...unreadable,
      persist: async () => {
        throw new Error("zavrnjeno");
      },
    }),
    "best-effort",
  );
});
