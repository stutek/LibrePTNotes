// src/ui/menu.js — meni kot spodnji list (bottom sheet): redka ali nevarna dejanja stranke in zapisa
// so v meniju ⋯, ne kot veliki gumbi pod palcem. Spodaj, ker trener drži telefon z eno roko.
// Je <dialog>: fokus, Escape in zaprtje ob dotiku ozadja so vgrajeni.
import { el } from "./dom.js";

/** `items`: [{ label, onClick, danger }]. Zapre se ob izbiri, Escape ali dotiku zunaj. */
export function openMenu({ title, items, closeLabel }) {
  const dialog = el("dialog", { cls: "sheet", attrs: { "aria-label": title } });
  dialog.append(
    el("p", { cls: "sheet-title", text: title }),
    ...items.map((item) =>
      el("button", {
        cls: `sheet-item${item.danger ? " danger" : ""}`,
        text: item.label,
        attrs: { type: "button" },
        on: {
          click: () => {
            dialog.close();
            item.onClick();
          },
        },
      }),
    ),
    el("button", {
      cls: "sheet-item sheet-cancel",
      text: closeLabel,
      attrs: { type: "button" },
      on: { click: () => dialog.close() },
    }),
  );
  // Dotik na samo ozadje (<dialog> je tarča klika, ko je zunaj vsebine) zapre meni.
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener("close", () => dialog.remove());
  document.body.append(dialog);
  dialog.showModal();
  return dialog;
}
