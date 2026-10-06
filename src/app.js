import { createBackupKeyStore } from "./data/backupKeyStore.js";
import { idbBackend, openDb } from "./data/idbBackend.js";
import { requestDurableStorage } from "./data/storageDurability.js";
// Vstopna točka LibrePTNotes: shramba, zavihki in pogled. Stanje je v shrambi (IndexedDB), ne tukaj.
import { createStore } from "./data/store.js";
import { formatDateTime } from "./domain/dates.js";
import { clientToMarkdown, safeFileName } from "./domain/exportText.js";
import { t } from "./i18n.js";
import { renderAboutSection } from "./ui/aboutSection.js";
import { renderBackupSection } from "./ui/backupSection.js";
import { renderClientList } from "./ui/clientList.js";
import { downloadText, el } from "./ui/dom.js";
import {
  flushPendingSave,
  focusNextNoteView,
  onForeignEdit,
  onSaveResult,
  renderNoteView,
} from "./ui/noteView.js";
import { setupPasswordDialog } from "./ui/passwordDialog.js";
import { renderTabs } from "./ui/tabs.js";
import { watchForUpdate } from "./ui/updateBar.js";

const tabsRoot = document.getElementById("tabs");
const viewRoot = document.getElementById("view");
let store;
let keyStore;
let listScroll = 0; // drsenje seznama strank, da se po vrnitvi z zavihka ne vrne na vrh
let dialog;

async function render(status) {
  const [clients, tabs] = await Promise.all([store.listClients(), store.getTabs()]);
  renderTabs(tabsRoot, {
    t,
    clients,
    tabs,
    onSelect: async (id) => {
      await flushPendingSave();
      await store.setActiveTab(id);
      render();
    },
    onClose: async (id) => {
      await flushPendingSave();
      await store.closeTab(id);
      render();
    },
  });
  const active = clients.find((c) => c.id === tabs.active);
  // Zapis je neprosoren blanket, ki se premika: preliv strani bi za njim pustil viden pravokotnik,
  // zato je v pogledu zapisa ozadje enotno.
  document.documentElement.classList.toggle("is-note-view", Boolean(active));
  if (active) {
    await renderNoteView(viewRoot, { t, store, client: active, show: render });
    return;
  }
  const [summaries, privacyAcked] = await Promise.all([
    store.clientSummaries(),
    store.hintDone("privacy"),
  ]);
  renderClientList(viewRoot, {
    t,
    clients,
    summaries,
    showPrivacyNotice: !privacyAcked,
    onAckPrivacy: async () => {
      await store.markHintDone("privacy");
      render();
    },
    onAdd: async (name) => {
      const client = await store.addClient(name);
      if (clients.length === 0) {
        // Prva stranka: takoj v zapis, pripravljen za pisanje (kot prazen dokument), brez dodatnega koraka.
        await store.openTab(client.id);
        await store.addNote(client.id);
        focusNextNoteView();
      }
      render();
    },
    onOpen: async (id) => {
      await store.openTab(id);
      render();
    },
    onRename: async (client) => {
      const name = prompt(t("renameClientPrompt"), client.name)?.trim();
      if (name && name !== client.name) await store.renameClient(client.id, name);
      render();
    },
    onExport: async (client) => {
      if (!confirm(t("exportConfirm").replace("{name}", client.name))) return;
      const notes = await store.listNotes(client.id);
      const text = clientToMarkdown(client, notes, { exportedAt: formatDateTime(new Date()) });
      downloadText(`${safeFileName(client.name)}.md`, text, "text/markdown");
    },
    onDelete: async (client) => {
      const notes = (await store.listNotes(client.id)).length;
      if (
        confirm(t("deleteClientConfirm").replace("{name}", client.name).replace("{notes}", notes))
      )
        await store.deleteClient(client.id);
      render();
    },
    extra: [
      await renderBackupSection({
        t,
        store,
        keyStore,
        dialog,
        onChange: render,
        status,
        compact: clients.length === 0,
      }),
      renderAboutSection({ t }),
    ],
  });
  const page = viewRoot.querySelector(".page");
  if (page) {
    page.scrollTop = listScroll;
    page.addEventListener("scroll", () => {
      listScroll = page.scrollTop;
    });
  }
}

// Brez IndexedDB (zasebno okno, onemogočena shramba) aplikacija ne more shraniti ničesar: to je treba
// povedati, ne pokazati prazne strani.
function showStorageError() {
  viewRoot.replaceChildren(
    el("p", { cls: "storage-error", text: t("storageUnavailable"), attrs: { role: "alert" } }),
  );
}

// Neuspešno shranjevanje je trak nad pogledom, dokler se naslednji zapis ne posreči.
function showSaveResult(error) {
  const existing = document.getElementById("save-error");
  if (!error) {
    existing?.remove();
    return;
  }
  if (existing) return;
  const bar = el("div", {
    cls: "save-error",
    text: t("saveFailed"),
    attrs: { id: "save-error", role: "alert" },
  });
  viewRoot.before(bar);
}

// Isti zapis je bil shranjen v drugem zavihku brskalnika: opozori, preden ga ta zavihek prepiše.
function showConflict() {
  if (document.getElementById("conflict-error")) return;
  const bar = el(
    "div",
    { cls: "conflict-error", attrs: { id: "conflict-error", role: "alert" } },
    el("span", { text: t("conflictNotice") }),
    el("button", {
      text: t("updateRefresh"),
      attrs: { type: "button" },
      on: { click: () => location.reload() },
    }),
  );
  viewRoot.before(bar);
}

async function start() {
  onSaveResult(showSaveResult);
  onForeignEdit(showConflict);
  let backend;
  try {
    backend = idbBackend(await openDb());
  } catch {
    showStorageError();
    return;
  }
  requestDurableStorage();
  store = createStore(backend);
  keyStore = createBackupKeyStore(backend);
  dialog = setupPasswordDialog({ t, keyStore });
  await render();
}

watchForUpdate({ t, beforeReload: flushPendingSave });
start();
