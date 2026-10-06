// Najmanjši pomočnik za gradnjo DOM; vsebina gre vedno prek textContent, nikoli prek innerHTML.
export function el(tag, { cls, text, attrs, on } = {}, ...children) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, v);
  for (const [k, v] of Object.entries(on || {})) node.addEventListener(k, v);
  node.append(...children.filter(Boolean));
  return node;
}

/** Prenese besedilo kot datoteko (Blob, ne zunanji strežnik). */
export function downloadText(filename, text, type = "text/plain") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = el("a", { attrs: { href: url, download: filename } });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
