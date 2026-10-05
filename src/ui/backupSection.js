// Odsek »Varnostna kopija« na seznamu strank: shrani šifrirano kopijo, obnovi iz datoteke, geslo.
import { BackupError, createBackup, restoreBackup } from "../data/backupFile.js";
import { hasBackupPassword } from "../data/backupKeyStore.js";
import { el } from "./dom.js";

const ERROR_TEXT = { "bad-file": "backupBadFile", foreign: "backupBadFile", "wrong-password": "backupWrongPassword", "no-password": "backupNeedsPassword" };

function download({ filename, text }) {
  const url = URL.createObjectURL(new Blob([text], { type: "application/json" }));
  const link = el("a", { attrs: { href: url, download: filename } });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// `status` je sporočilo prejšnjega izrisa ({key, vars}): po shranjevanju se odsek izriše znova.
export async function renderBackupSection({ t, store, keyStore, dialog, onChange, status: previous }) {
  const hasPassword = await hasBackupPassword(keyStore);
  const status = el("p", { cls: "status", attrs: { role: "status" } });
  const say = (key, error = false, vars = {}) => {
    status.textContent = Object.entries(vars).reduce((text, [k, v]) => text.replace(`{${k}}`, v), key ? t(key) : "");
    status.classList.toggle("is-error", error);
  };
  if (previous) say(previous.key, false, previous.vars);
  const fail = (e) => (e instanceof BackupError ? (ERROR_TEXT[e.code] ? say(ERROR_TEXT[e.code], true) : say("")) : say("backupBadFile", true));

  async function save() {
    try {
      if (!(await hasBackupPassword(keyStore)) && !(await dialog.askToSet())) return say("backupNeedsPassword", true);
      download(await createBackup({ store, keyStore }));
      onChange({ key: "backupSaved" });
    } catch (e) {
      fail(e);
    }
  }

  async function restore(file) {
    try {
      const counts = await restoreBackup(await file.text(), {
        store,
        keyStore,
        askPassword: (envelope) => dialog.askToUnlock(envelope),
        confirmReplace: async (data) => confirm(t("backupRestoreConfirm").replace("{clients}", data.clients.length).replace("{notes}", data.notes.length)),
      });
      onChange({ key: "backupRestored", vars: counts });
    } catch (e) {
      fail(e);
    }
  }

  const fileInput = el("input", { attrs: { type: "file", accept: "application/json,.json", hidden: "" }, on: { change: (e) => { const [file] = e.target.files; e.target.value = ""; if (file) restore(file); } } });
  const button = (key, onClick, cls) => el("button", { cls, text: t(key), attrs: { type: "button" }, on: { click: onClick } });
  return el(
    "section",
    { cls: "backup" },
    el("h2", { text: t("backupTitle") }),
    el("p", { text: t(hasPassword ? "backupPasswordSet" : "backupPasswordUnset") }),
    el("div", { cls: "row" }, button("backupSave", save, "primary"), button("backupRestore", () => fileInput.click())),
    el("div", { cls: "row" }, button("backupPasswordChange", async () => { await dialog.askToSet({ changing: true }); onChange(); }), hasPassword && button("backupPasswordForget", async () => { await dialog.forget(); onChange(); })),
    fileInput,
    status,
  );
}
