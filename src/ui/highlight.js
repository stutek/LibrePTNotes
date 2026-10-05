// Izris barvanega besedila v `pre` iz odsekov domain/markdown.js; vsebina gre prek textContent.
import { tokenize } from "../domain/markdown.js";
import { el } from "./dom.js";

export function paintHighlight(pre, text) {
  pre.replaceChildren(
    ...tokenize(text).map((seg) =>
      seg.cls ? el("span", { cls: seg.cls, text: seg.text }) : document.createTextNode(seg.text),
    ),
    // Zaključni prelom vrstice brez znaka za njim pre ne prikaže, textarea pa ga ima.
    document.createTextNode(text.endsWith("\n") ? " " : ""),
  );
}

export function highlightBlock(text) {
  const pre = el("pre", { cls: "md-highlight" });
  paintHighlight(pre, text);
  return pre;
}
