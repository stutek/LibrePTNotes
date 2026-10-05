// Prijava service workerja in trak »Na voljo je nova različica«. Nov worker po namestitvi počaka
// (sw.js ne kliče skipWaiting); gumb Osveži mu pošlje SKIP_WAITING in po zamenjavi naloži stran znova.
import { el } from "./dom.js";

export function watchForUpdate({ t, beforeReload = async () => {} }) {
  if (!("serviceWorker" in navigator)) return;
  let bar = null;

  function offer(worker) {
    // Brez krmilnika je to prva namestitev, ne posodobitev.
    if (bar || !navigator.serviceWorker.controller) return;
    const button = el("button", {
      cls: "primary update-refresh",
      text: t("updateRefresh"),
      attrs: { type: "button" },
    });
    bar = el(
      "div",
      { cls: "update-bar", attrs: { role: "status" } },
      el("span", { text: t("updateAvailable") }),
      button,
    );
    button.addEventListener("click", async () => {
      button.disabled = true;
      await beforeReload();
      worker.postMessage({ type: "SKIP_WAITING" });
    });
    document.getElementById("app").prepend(bar);
  }

  let reloading = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    // Prvi claim po prvi namestitvi ni zamenjava različice.
    if (!bar || reloading) return;
    reloading = true;
    location.reload();
  });

  // Relativno in z obsegom ./, da deluje na kateri koli poti. updateViaCache: brskalnik
  // sw.js vedno preveri na strežniku.
  navigator.serviceWorker
    .register("./sw.js", { scope: "./", updateViaCache: "none" })
    .then((reg) => {
      if (reg.waiting) offer(reg.waiting);
      reg.addEventListener("updatefound", () => {
        const worker = reg.installing;
        worker?.addEventListener(
          "statechange",
          () => worker.state === "installed" && offer(worker),
        );
      });
      document.addEventListener(
        "visibilitychange",
        () => document.visibilityState === "visible" && reg.update().catch(() => {}),
      );
    })
    .catch(() => {});
}
