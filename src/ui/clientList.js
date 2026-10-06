// src/ui/clientList.js — seznam strank: vrstica = dotik odpre beležke, ⋯ odpre meni (preimenuj, izvozi,
// izbriši). Prvi zagon (brez strank) je dobrodošlica z enim poljem; zasebnostno obvestilo za trenerja
// stoji na vrhu, dokler ga ne potrdi.
import { initialOf } from "../domain/names.js";
import { el } from "./dom.js";
import { openMenu } from "./menu.js";

function clientMeta(t, summary) {
  if (!summary?.count) return t("clientMetaNone");
  return t("clientMeta").replace("{count}", summary.count).replace("{last}", summary.last);
}

function privacyNotice({ t, onAck }) {
  return el(
    "section",
    { cls: "notice", attrs: { role: "note" } },
    el("h2", { text: t("privacyNoticeTitle") }),
    el("p", { text: t("privacyNoticeBody") }),
    el(
      "div",
      { cls: "row" },
      el("a", { cls: "btn-link", text: t("privacyReadMore"), attrs: { href: "./privacy.html" } }),
      el("button", {
        cls: "primary",
        text: t("privacyAck"),
        attrs: { type: "button" },
        on: { click: onAck },
      }),
    ),
  );
}

export function renderClientList(
  root,
  {
    t,
    clients,
    summaries,
    showPrivacyNotice,
    onAckPrivacy,
    onAdd,
    onOpen,
    onRename,
    onExport,
    onDelete,
    extra,
  },
) {
  const welcome = clients.length === 0;
  const input = el("input", {
    attrs: {
      type: "text",
      id: "client-name",
      autocomplete: "off",
      "aria-label": t("clientNameLabel"),
      placeholder: t(welcome ? "clientNameFirst" : "clientNamePlaceholder"),
    },
  });
  let adding = false;
  let warnedAbout = null; // podvojeno ime, na katero je bil trener že opozorjen
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
      cls: `add-client${welcome ? " is-welcome" : ""}`,
      on: {
        submit: (e) => {
          e.preventDefault();
          const name = input.value.trim();
          if (!name) {
            error.textContent = t("clientNameRequired");
            error.hidden = false;
            return;
          }
          // Dve stranki z istim imenom se ne ločita: opozori, ob ponovnem dotiku pa dovoli (res sta dve).
          const key = name.toLocaleLowerCase("sl");
          if (clients.some((c) => c.name.toLocaleLowerCase("sl") === key) && warnedAbout !== key) {
            warnedAbout = key;
            error.textContent = t("clientNameExists");
            error.hidden = false;
            return;
          }
          // Trije hitri dotiki so dali tri enake stranke: obrazec je prvi odgovor, ostali so odveč.
          if (adding) return;
          adding = true;
          Promise.resolve(onAdd(name)).catch(() => {
            adding = false;
          });
        },
      },
    },
    input,
    el("button", {
      cls: "primary",
      text: t(welcome ? "addFirstClient" : "addClientShort"),
      attrs: { type: "submit" },
    }),
    error,
  );
  const rows = clients.map((c) =>
    el(
      "li",
      { cls: "client-row" },
      el(
        "button",
        {
          cls: "open-notes client-open",
          attrs: { type: "button", "aria-label": `${t("openClientNotes")}: ${c.name}` },
          on: { click: () => onOpen(c.id) },
        },
        el("span", { cls: "avatar", text: initialOf(c.name), attrs: { "aria-hidden": "true" } }),
        el(
          "span",
          { cls: "client-text" },
          el("span", { cls: "client-name", text: c.name }),
          el("span", { cls: "client-meta", text: clientMeta(t, summaries?.[c.id]) }),
        ),
        el("span", { cls: "chevron", text: "›", attrs: { "aria-hidden": "true" } }),
      ),
      el("button", {
        cls: "client-menu",
        text: "⋯",
        attrs: { type: "button", "aria-label": `${t("clientMenu")}: ${c.name}` },
        on: {
          click: () =>
            openMenu({
              title: c.name,
              closeLabel: t("menuClose"),
              items: [
                { label: t("renameClient"), onClick: () => onRename(c) },
                { label: t("clientExport"), onClick: () => onExport(c) },
                { label: t("deleteClientItem"), danger: true, onClick: () => onDelete(c) },
              ],
            }),
        },
      }),
    ),
  );
  const hero = welcome
    ? el(
        "section",
        { cls: "welcome" },
        el("img", {
          cls: "welcome-logo",
          attrs: { src: "./icons/icon-192.png", alt: "", width: "64", height: "64" },
        }),
        el("h1", { text: t("welcomeTitle") }),
        el("p", { text: t("welcomeLead") }),
      )
    : null;
  root.replaceChildren(
    el(
      "div",
      { cls: "page" },
      hero,
      form,
      showPrivacyNotice ? privacyNotice({ t, onAck: onAckPrivacy }) : null,
      rows.length ? el("ul", { cls: "client-list" }, ...rows) : null,
      ...[].concat(extra),
    ),
  );
}
