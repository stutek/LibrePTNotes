import { test } from "node:test";
import assert from "node:assert/strict";
import { tokenize } from "../src/domain/markdown.js";

const classes = (text) => tokenize(text).filter((s) => s.cls).map((s) => [s.cls, s.text]);

test("besedilo se nikoli ne spremeni: združeni odseki so enaki vhodu", () => {
  const samples = [
    "",
    "navadno besedilo\n",
    "# Naslov\n\n**krepko** in *ležeče* in `koda`\n- a\n- b\n1. c\n> citat\n```js\nconst a = 1;\n```\n[pove](https://x.si) konec\n\n",
    "  - zamaknjeno **ni zaprto\n_a_b_ ** ` \n```\nneskončen blok",
    "čšž 😀 **ž**",
  ];
  for (const s of samples) assert.equal(tokenize(s).map((x) => x.text).join(""), s);
});

test("naslovi", () => {
  assert.deepEqual(classes("# Dan 1\ntekst\n### Tri"), [["md-heading", "# Dan 1"], ["md-heading", "### Tri"]]);
  assert.deepEqual(classes("#brez presledka"), []);
  assert.deepEqual(classes("####### sedem"), []);
});

test("krepko in ležeče", () => {
  assert.deepEqual(classes("a **b** c"), [["md-bold", "**b**"]]);
  assert.deepEqual(classes("a __b__ c"), [["md-bold", "__b__"]]);
  assert.deepEqual(classes("a *b* c"), [["md-italic", "*b*"]]);
  assert.deepEqual(classes("a _b_ c"), [["md-italic", "_b_"]]);
  assert.deepEqual(classes("snake_case_name"), [], "podčrtaj v besedi ni ležeče");
  assert.deepEqual(classes("2 * 3 * 4"), [], "zvezdica s presledki ni ležeče");
});

test("seznami: obarva se samo oznaka, vsebina je lahko oblikovana", () => {
  assert.deepEqual(classes("- stvar"), [["md-marker", "-"]]);
  assert.deepEqual(classes("  * stvar **x**"), [["md-marker", "*"], ["md-bold", "**x**"]]);
  assert.deepEqual(classes("12. stvar"), [["md-marker", "12."]]);
  assert.deepEqual(classes("-brez presledka"), []);
});

test("citati", () => {
  assert.deepEqual(classes("> misel\nnavadno"), [["md-quote", "> misel"]]);
});

test("vrstična koda in povezave", () => {
  assert.deepEqual(classes("a `x *y*` b"), [["md-code", "`x *y*`"]]);
  assert.deepEqual(classes("glej [stran](https://a.si/b) tu"), [["md-link", "[stran](https://a.si/b)"]]);
});

test("bloki kode: ograja in vsebina, tudi neprekinjen blok do konca", () => {
  assert.deepEqual(classes("```js\n# ni naslov\n**ni krepko**\n```\n# naslov"), [
    ["md-fence", "```js"],
    ["md-code", "# ni naslov"],
    ["md-code", "**ni krepko**"],
    ["md-fence", "```"],
    ["md-heading", "# naslov"],
  ]);
  assert.deepEqual(classes("```\nnezaprt"), [["md-fence", "```"], ["md-code", "nezaprt"]]);
});
