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
