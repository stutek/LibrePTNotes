import { createBackupKeyStore } from "./data/backupKeyStore.js";
import { idbBackend, openDb } from "./data/idbBackend.js";
import { requestDurableStorage } from "./data/storageDurability.js";
// Vstopna točka LibrePTNotes: shramba, zavihki in pogled. Stanje je v shrambi (IndexedDB), ne tukaj.
import { createStore } from "./data/store.js";
import { t } from "./i18n.js";
import { renderAboutSection } from "./ui/aboutSection.js";
import { renderBackupSection } from "./ui/backupSection.js";
import { renderClientList } from "./ui/clientList.js";
import { el } from "./ui/dom.js";
import { flushPendingSave, renderNoteView } from "./ui/noteView.js";
import { setupPasswordDialog } from "./ui/passwordDialog.js";
import { renderTabs } from "./ui/tabs.js";
import { watchForUpdate } from "./ui/updateBar.js";

const tabsRoot = document.getElementById("tabs");
const viewRoot = document.getElementById("view");
let store;
let keyStore;
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
  if (active) {
    await renderNoteView(viewRoot, { t, store, client: active, show: render });
    return;
  }
  renderClientList(viewRoot, {
    t,
    clients,
    onAdd: async (name) => {
      await store.addClient(name);
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
    onDelete: async (client) => {
      const notes = (await store.listNotes(client.id)).length;
      if (
        confirm(t("deleteClientConfirm").replace("{name}", client.name).replace("{notes}", notes))
      )
        await store.deleteClient(client.id);
      render();
    },
    extra: [
      await renderBackupSection({ t, store, keyStore, dialog, onChange: render, status }),
      renderAboutSection({ t }),
    ],
  });
}

// Brez IndexedDB (zasebno okno, onemogočena shramba) aplikacija ne more shraniti ničesar: to je treba
// povedati, ne pokazati prazne strani.
function showStorageError() {
  viewRoot.replaceChildren(
    el("p", { cls: "storage-error", text: t("storageUnavailable"), attrs: { role: "alert" } }),
  );
}

async function start() {
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
