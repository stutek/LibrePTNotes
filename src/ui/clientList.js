// Seznam strank, dodajanje stranke in gumb »Odpri beležke stranke«.
import { el } from "./dom.js";

export function renderClientList(root, { t, clients, onAdd, onOpen, onRename, onDelete, extra }) {
  const input = el("input", {
    attrs: {
      type: "text",
      id: "client-name",
      autocomplete: "off",
      "aria-label": t("clientNameLabel"),
      placeholder: t("clientNameLabel"),
    },
  });
  const form = el(
    "form",
    {
      cls: "add-client",
      on: {
        submit: (e) => {
          e.preventDefault();
          const name = input.value.trim();
          if (name) onAdd(name);
        },
      },
    },
    input,
    el("button", { cls: "primary", text: t("addClient"), attrs: { type: "submit" } }),
  );
  const list = clients.length
    ? el(
        "ul",
        { cls: "client-list" },
        ...clients.map((c) =>
          el(
            "li",
            { cls: "client-row" },
            el("span", { cls: "client-name", text: c.name }),
            el(
              "div",
              { cls: "client-actions" },
              el("button", {
                cls: "open-notes primary",
                text: t("openClientNotes"),
                attrs: { type: "button" },
                on: { click: () => onOpen(c.id) },
              }),
              el("button", {
                cls: "rename-client",
                text: t("renameClient"),
                attrs: { type: "button", "aria-label": `${t("renameClient")}: ${c.name}` },
                on: { click: () => onRename(c) },
              }),
              el("button", {
                cls: "delete-client danger",
                text: t("deleteClient"),
                attrs: { type: "button", "aria-label": `${t("deleteClient")}: ${c.name}` },
                on: { click: () => onDelete(c) },
              }),
            ),
          ),
        ),
      )
    : el("p", { cls: "empty", text: t("noClients") });
  root.replaceChildren(el("div", { cls: "page" }, form, list, ...[].concat(extra)));
}
