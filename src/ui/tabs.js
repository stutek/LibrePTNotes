// Zavihki: seznam strank in odprte stranke. Izbira samo s klikom; prehoda na sosednji zavihek ni.
import { el } from "./dom.js";

export function renderTabs(root, { t, clients, tabs, onSelect, onClose }) {
  const nameOf = (id) => clients.find((c) => c.id === id)?.name ?? "";
  const tab = (id, label, closable) =>
    el(
      "div",
      { cls: `tab${tabs.active === id ? " is-active" : ""}` },
      el("button", { cls: "tab-name", text: label, attrs: { type: "button", "aria-current": String(tabs.active === id) }, on: { click: () => onSelect(id) } }),
      closable && el("button", { cls: "tab-close", text: "✕", attrs: { type: "button", "aria-label": `${t("closeTab")}: ${label}` }, on: { click: () => onClose(id) } }),
    );
  root.replaceChildren(
    tab(null, t("clientsTab"), false),
    ...tabs.open.filter((id) => clients.some((c) => c.id === id)).map((id) => tab(id, nameOf(id), true)),
  );
  // Aktivni zavihek mora biti viden, ko jih je več, kot gre v vrstico.
  root.querySelector(".tab.is-active")?.scrollIntoView({ inline: "nearest", block: "nearest" });
}
