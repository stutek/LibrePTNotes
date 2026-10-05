import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { join, relative } from "node:path";
// Kar zapiše trener (ime stranke, besedilo zapisa) ali pride iz uvožene datoteke, nikoli ne sme postati
// oznaka. Statično: nobenega stika s HTML ali izvršljivim besedilom. Dinamično: vrednosti `<img onerror>`
// pridejo do DOM samo prek textContent (brskalniški preizkus je tests/medium/test_xss_sink.py).
import { test } from "node:test";

const SRC = new URL("../../../src/", import.meta.url).pathname;

function files(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? files(join(dir, e.name)) : [join(dir, e.name)],
  );
}

// Koda brez komentarjev (vrstični in blokovni), da razlaga v komentarju ne sproži iskanja.
function code(path) {
  return readFileSync(path, "utf8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
}

const JS = files(SRC).filter((f) => f.endsWith(".js"));

// The absence of this sink is the contract (stored XSS, no server traffic): an avoided side effect.
test("nobena datoteka ne uporablja HTML ali izvršljivih sinkov", () => {
  const forbidden =
    /\b(innerHTML|outerHTML|insertAdjacentHTML|document\.write|createContextualFragment|srcdoc)\b|\beval\s*\(|new\s+Function\s*\(|\bsetTimeout\s*\(\s*["'`]/;
  for (const f of JS) assert.doesNotMatch(code(f), forbidden, relative(SRC, f));
});

// The absence of this sink is the contract (stored XSS, no server traffic): an avoided side effect.
test("videz samo v CSS: edini inline slog je --plan-pull v kretnji", () => {
  for (const f of JS) {
    const text = code(f);
    const uses = text.match(/\.style\b[^;\n]*|setAttribute\(\s*["']style["']|cssText/g) || [];
    if (relative(SRC, f) === "gesture/planPeek.js") {
      assert.ok(uses.length > 0);
      for (const use of uses) assert.match(use, /\.style\.setProperty\("--plan-pull"/, use);
    } else assert.deepEqual(uses, [], relative(SRC, f));
  }
});

// The absence of this sink is the contract (stored XSS, no server traffic): an avoided side effect.
test("pomočnik el() ne prejme atributov za dogodke ali slog", () => {
  for (const f of JS) {
    const attrs = code(f).match(/attrs:\s*\{[^}]*\}/g) || [];
    for (const a of attrs)
      assert.doesNotMatch(
        a,
        /\b(on[a-z]+|style|srcdoc|formaction)\s*:/i,
        `${relative(SRC, f)}: ${a}`,
      );
  }
});

test("index.html: brez vgrajenih skript, slogov in dogodkov; CSP brez unsafe-*", () => {
  const html = readFileSync(join(SRC, "index.html"), "utf8");
  // is the contract: index.html's shipped policy; an avoided side effect (stored XSS / silent version switch).
  assert.doesNotMatch(html, /<script(?![^>]*\bsrc=)/i);
  // is the contract: index.html's shipped policy; an avoided side effect (stored XSS / silent version switch).
  assert.doesNotMatch(html, /<style/i);
  // is the contract: index.html's shipped policy; an avoided side effect (stored XSS / silent version switch).
  assert.doesNotMatch(html, /\s(on[a-z]+|style)\s*=/i);
  // is the contract: index.html's shipped policy; an avoided side effect (stored XSS / silent version switch).
  const csp = html.match(/http-equiv="Content-Security-Policy"\s+content="([^"]+)"/)?.[1];
  assert.ok(csp, "manjka CSP meta");
  // is the contract: index.html's shipped policy; an avoided side effect (stored XSS / silent version switch).
  assert.doesNotMatch(csp, /unsafe-|\*|https?:/);
  // is the contract: index.html's shipped policy; an avoided side effect (stored XSS / silent version switch).
  assert.match(csp, /default-src 'self'/);
  // is the contract: index.html's shipped policy; an avoided side effect (stored XSS / silent version switch).
  assert.match(csp, /script-src 'self'(;|$)/);
  // is the contract: index.html's shipped policy; an avoided side effect (stored XSS / silent version switch).
  assert.match(csp, /object-src 'none'/);
});

// The absence of this sink is the contract (stored XSS, no server traffic): an avoided side effect.
test("nič ne gre na strežnik: brez absolutnih naslovov in omrežnih vtičnic", () => {
  for (const f of JS) {
    const text = code(f);
    assert.doesNotMatch(text, /["'`]https?:\/\//, `${relative(SRC, f)}: absoluten naslov`);
    assert.doesNotMatch(
      text,
      /\b(WebSocket|XMLHttpRequest|EventSource|sendBeacon)\b/,
      relative(SRC, f),
    );
  }
});

// Najmanjši lažni DOM: vsako vozlišče beleži textContent in zavrne vsak HTML vstop.
function fakeDom() {
  const made = [];
  const trap = (name) => {
    throw new Error(`HTML sink: ${name}`);
  };
  const node = (tag) => {
    const n = {
      tag,
      attrs: {},
      children: [],
      classes: new Set(),
      textContent: "",
      className: "",
      setAttribute(k, v) {
        this.attrs[k] = String(v);
      },
      addEventListener() {},
      append(...c) {
        this.children.push(...c);
      },
      replaceChildren(...c) {
        this.children = c;
      },
      querySelector() {
        return null;
      },
      classList: { toggle() {}, add() {}, remove() {}, contains: () => false },
      scrollIntoView() {},
    };
    for (const sink of ["innerHTML", "outerHTML"])
      Object.defineProperty(n, sink, { set: () => trap(sink) });
    n.insertAdjacentHTML = () => trap("insertAdjacentHTML");
    made.push(n);
    return n;
  };
  globalThis.document = {
    createElement: node,
    createTextNode: (text) => ({ text, textContent: text }),
  };
  return { made, root: node("div") };
}

const PAYLOADS = [
  '<img src=x onerror="alert(1)">',
  "<script>alert(1)</script>",
  '"><svg onload=alert(1)>',
  "javascript:alert(1)",
];

test("ime stranke in besedilo zapisa pridejo v DOM samo kot besedilo", async () => {
  const { renderClientList } = await import("../../../src/ui/clientList.js");
  const { renderTabs } = await import("../../../src/ui/tabs.js");
  const { highlightBlock } = await import("../../../src/ui/highlight.js");
  const t = (k) => k;
  for (const payload of PAYLOADS) {
    const dom = fakeDom();
    const clients = [{ id: "a", name: payload }];
    renderClientList(dom.root, {
      t,
      clients,
      onAdd() {},
      onOpen() {},
      onRename() {},
      onDelete() {},
      extra: [],
    });
    renderTabs(dom.root, {
      t,
      clients,
      tabs: { open: ["a"], active: "a" },
      onSelect() {},
      onClose() {},
    });
    highlightBlock(`# ${payload}\n**${payload}**\n\`${payload}\``);
    const texts = dom.made.map((n) => n.textContent);
    assert.ok(texts.includes(payload), "ime je izrisano kot besedilo");
    assert.ok(
      dom.made.every((n) => !["img", "script", "svg"].includes(n.tag)),
      "ni ustvarjenih oznak iz vsebine",
    );
  }
});
