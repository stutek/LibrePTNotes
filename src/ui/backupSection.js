// Odsek »Varnostna kopija« na seznamu strank: shrani šifrirano kopijo, obnovi iz datoteke, geslo.
import { BackupError, createBackup, restoreBackup } from "../data/backupFile.js";
import { hasBackupPassword } from "../data/backupKeyStore.js";
import { downloadText, el } from "./dom.js";
import { openMenu } from "./menu.js";

const ERROR_TEXT = {
  "bad-file": "backupBadFile",
  newer: "backupNewer",
  foreign: "backupBadFile",
  "wrong-password": "backupWrongPassword",
  "no-password": "backupNeedsPassword",
};

// `status` je sporočilo prejšnjega izrisa ({key, vars}): po shranjevanju se odsek izriše znova.
export async function renderBackupSection({
  t,
  store,
  keyStore,
  dialog,
  onChange,
  status: previous,
  compact = false,
}) {
  const hasPassword = await hasBackupPassword(keyStore);
  const status = el("p", { cls: "status", attrs: { role: "status" } });
  const say = (key, error = false, vars = {}) => {
    status.textContent = Object.entries(vars).reduce(
      (text, [k, v]) => text.replace(`{${k}}`, v),
      key ? t(key) : "",
    );
    status.classList.toggle("is-error", error);
  };
  if (previous) say(previous.key, false, previous.vars);
  const fail = (e) =>
    e instanceof BackupError
      ? ERROR_TEXT[e.code]
        ? say(ERROR_TEXT[e.code], true)
        : say("")
      : say("backupBadFile", true);

  async function save() {
    try {
      if (!(await hasBackupPassword(keyStore)) && !(await dialog.askToSet()))
        return say("backupNeedsPassword", true);
      const { filename, text } = await createBackup({ store, keyStore });
      downloadText(filename, text, "application/json");
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
        confirmReplace: async (data) =>
          confirm(
            t("backupRestoreConfirm")
              .replace("{clients}", data.clients.length)
              .replace("{notes}", data.notes.length),
          ),
      });
      onChange({ key: "backupRestored", vars: counts });
    } catch (e) {
      fail(e);
    }
  }

  const fileInput = el("input", {
    attrs: { type: "file", accept: "application/json,.json", hidden: "" },
    on: {
      change: (e) => {
        const [file] = e.target.files;
        e.target.value = "";
        if (file) restore(file);
      },
    },
  });
  const button = (key, onClick, cls) =>
    el("button", { cls, text: t(key), attrs: { type: "button" }, on: { click: onClick } });
  // Prvi zagon (brez strank): nič za shraniti, na novem telefonu pa je obnova prva stvar, ki jo trener išče.
  if (compact) {
    return el(
      "section",
      { cls: "backup restore-only" },
      el("p", { text: t("restoreHint") }),
      el(
        "div",
        { cls: "row" },
        button("backupRestore", () => fileInput.click()),
      ),
      fileInput,
      status,
    );
  }
  const dataMenu = () =>
    openMenu({
      title: t("backupTitle"),
      closeLabel: t("menuClose"),
      items: [
        {
          label: t("backupPasswordChange"),
          onClick: async () => {
            await dialog.askToSet({ changing: true });
            onChange();
          },
        },
        ...(hasPassword
          ? [
              {
                label: t("backupPasswordForget"),
                onClick: async () => {
                  if (!confirm(t("backupPasswordForgetConfirm"))) return;
                  await dialog.forget();
                  onChange();
                },
              },
            ]
          : []),
        {
          label: t("deleteAllData"),
          danger: true,
          onClick: async () => {
            // Dve potrditvi: tega ni mogoče razveljaviti, kopije pa ostanejo, kjer so.
            if (!confirm(t("deleteAllConfirm")) || !confirm(t("deleteAllConfirm2"))) return;
            await store.deleteAllData();
            onChange({ key: "dataDeleted" });
          },
        },
      ],
    });
  return el(
    "section",
    { cls: "backup" },
    el(
      "div",
      { cls: "backup-head" },
      el("h2", { text: t("backupTitle") }),
      el("button", {
        cls: "client-menu",
        text: "⋯",
        attrs: { type: "button", "aria-label": t("dataMenu") },
        on: { click: dataMenu },
      }),
    ),
    el("p", { text: t(hasPassword ? "backupPasswordSet" : "backupPasswordUnset") }),
    el(
      "div",
      { cls: "row" },
      button("backupSave", save, "primary"),
      button("backupRestore", () => fileInput.click()),
    ),
    fileInput,
    status,
  );
}
