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
  const error = el("p", {
    cls: "form-error",
    text: t("clientNameRequired"),
    attrs: { role: "alert" },
  });
  error.hidden = true;
  input.addEventListener("input", () => {
    error.hidden = true;
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
          else error.hidden = false;
        },
      },
    },
    input,
    el("button", { cls: "primary", text: t("addClient"), attrs: { type: "submit" } }),
    error,
  );
  const list = clients.length
    ? el(
        "ul",
        { cls: "client-list" },
        ...clients.map((c) =>
          el(
            "li",
            { cls: "client-row" },
            el("span", {
              cls: "avatar",
              text: [...c.name][0].toUpperCase(),
              attrs: { "aria-hidden": "true" },
            }),
            el("span", { cls: "client-name", text: c.name }),
            el(
              "div",
              { cls: "client-actions" },
              el("button", {
                cls: "open-notes primary",
                text: t("openClientNotes"),
                attrs: { type: "button", "aria-label": `${t("openClientNotes")}: ${c.name}` },
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
