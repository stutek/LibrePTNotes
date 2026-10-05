// Vstopna točka LibrePTNotes: shramba, zavihki in pogled. Stanje je v shrambi (IndexedDB), ne tukaj.
import { createStore } from "./data/store.js";
import { idbBackend, openDb } from "./data/idbBackend.js";
import { t } from "./i18n.js";
import { renderClientList } from "./ui/clientList.js";
import { renderTabs } from "./ui/tabs.js";

const tabsRoot = document.getElementById("tabs");
const viewRoot = document.getElementById("view");
let store;

async function render() {
  const [clients, tabs] = await Promise.all([store.listClients(), store.getTabs()]);
  renderTabs(tabsRoot, {
    t,
    clients,
    tabs,
    onSelect: async (id) => { await store.setActiveTab(id); render(); },
    onClose: async (id) => { await store.closeTab(id); render(); },
  });
  const active = clients.find((c) => c.id === tabs.active);
  if (active) {
    viewRoot.replaceChildren(); // pogled zapisov pride v koraku 4
    return;
  }
  renderClientList(viewRoot, {
    t,
    clients,
    onAdd: async (name) => { await store.addClient(name); render(); },
    onOpen: async (id) => { await store.openTab(id); render(); },
  });
}

async function start() {
  store = createStore(idbBackend(await openDb()));
  await render();
}

if ("serviceWorker" in navigator) {
  // Relativno in z obsegom ./, da deluje na kateri koli poti (TODO.md §2).
  navigator.serviceWorker.register("./sw.js", { scope: "./" }).catch(() => {});
}
start();
