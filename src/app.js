// Vstopna točka LibrePTNotes: registrira service worker in izrisuje aplikacijo.
import { t } from "./i18n.js";

function render() {
  document.getElementById("view").textContent = t("noClients");
}

if ("serviceWorker" in navigator) {
  // Relativno in z obsegom ./, da deluje na kateri koli poti (TODO.md §2).
  navigator.serviceWorker.register("./sw.js", { scope: "./" }).catch(() => {});
}
render();
