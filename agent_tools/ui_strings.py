"""`python -m agent_tools.ui_strings` — besedilo vmesnika, ki ne gre skozi slovar, in ključi, ki ne obstajajo.

Zakaj: vmesnik je slovenski in vsa besedila so v `src/i18n.js` (`STRINGS`, `t()`). Besedilo, zapisano
neposredno v kodo UI, tja ne pride: ne poznamo ga na enem mestu, ne da se ga popraviti, ne da se
preveriti, in prej ali slej v aplikaciji ostane angleška beseda. Neznan ključ `t("kljuc")` pa se
izpiše kot sam ključ, brez napake. V LibrePT je to prešlo na 332 prevodnih lukenj, preden je kdo
pogledal; tu je repo majhen, zato kontrola velja strogo, brez ratchet-a (`BASELINE = 0`).

Kaj velja za vidno besedilo:

  * JS: literal v `text:`, `textContent =`, `innerText`, v atributih `placeholder`, `aria-label`,
    `title`, `alt`, `label` (v objektu ali `setAttribute`), v `confirm()`, `alert()`, `prompt()`
    ter besedilo med oznakami v predlogi (`>Beseda<`). Literal brez črk (✕, —, ·) ni besedilo.
  * `src/index.html`: besedilo med oznakami in vrednosti `placeholder`, `aria-label`, `title`, `alt`.
    Dialog z geslom dobi besedila iz JS prek `t()`, zato ostane v HTML prazen; kar je tam napisano,
    se prijavi. `<title>`, `<script>` in `<style>` ne štejejo (ime izdelka ni prevod).
  * `t("ključ")` mora imeti ključ v `STRINGS`; ključ v `STRINGS`, ki ga nihče ne bere, je mrtva
    teža (preverjeno samo, če koda nikjer ne sestavlja ključev dinamično).

`src/i18n.js` je slovar in se ne išče; `src/sw.js` nima vmesnika. `src/gesture/planPeek.js` je kopija
iz LibrePT in prav tako ne sme vsebovati besedil (prejme jih iz poklicatelja).
"""

import re
import sys
from pathlib import Path

from agent_tools._tree import ROOT

BASELINE = 0
SKIP = {"src/i18n.js", "src/sw.js", "src/version.js"}
LETTERS = re.compile(r"[^\W\d_]{2,}", re.UNICODE)
STRING = r"""(?:"((?:[^"\\\n]|\\.)*)"|'((?:[^'\\\n]|\\.)*)'|`((?:[^`\\]|\\.)*)`)"""
KEYS = (
    r"(?:text|textContent|innerText|placeholder|label|title|alt|aria-label|ariaLabel)"
)
# `text: "…"`, `"aria-label": "…"`, `el.textContent = "…"`, `el.title = '…'` (ne `==`)
PROP = re.compile(rf"""(?:\b|["']){KEYS}["']?\s*(?::|=(?!=))\s*{STRING}""")
SET_ATTRIBUTE = re.compile(
    rf"""setAttribute\(\s*["'](?:placeholder|aria-label|title|alt)["']\s*,\s*{STRING}"""
)
DIALOG = re.compile(rf"""\b(?:confirm|alert|prompt)\(\s*{STRING}""")
# Besedilo med oznakama v predlogi: `<b>Beseda</b>`; `a > b ... c <` v kodi ni oznaka.
TAG_TEXT = re.compile(r"<[A-Za-z][^<>]*>([^<>{}\n]*[^\W\d_]{2,}[^<>{}\n]*)<")
T_CALL = re.compile(r"""\bt\(\s*["']([\w.-]+)["']\s*\)""")
DYNAMIC_T = re.compile(r"\bt\(\s*(?!\s*[\"'])")
HTML_ATTR = re.compile(r"""\b(?:placeholder|aria-label|title|alt)\s*=\s*"([^"]*)\"""")
HTML_SKIP_BLOCK = re.compile(r"<(script|style|title)\b.*?</\1>", re.S | re.I)


def literal_text(match):
    """Besedilo literala iz skupin STRING (dvojni, enojni ali povratni narekovaj)."""
    return next((g for g in match.groups() if g is not None), "")


def has_words(text):
    """Ima besede zunaj `${…}`: v `${t("a")}: ${x}` je dvopičje vezivo, ne besedilo."""
    return bool(LETTERS.search(re.sub(r"\$\{[^}]*\}", "", text)))


def js_findings(text):
    """[(vrstica, kratek opis)] besedil, ki jih v kodi piše namesto t()."""
    found = []
    for pattern in (PROP, SET_ATTRIBUTE, DIALOG):
        for match in pattern.finditer(text):
            if has_words(literal_text(match)):
                found.append(
                    (text.count("\n", 0, match.start()) + 1, literal_text(match))
                )
    for match in TAG_TEXT.finditer(text):
        found.append((text.count("\n", 0, match.start()) + 1, match.group(1).strip()))
    return sorted(set(found))


def html_findings(text):
    """[(vrstica, besedilo)] statičnih besedil v HTML (brez <title>, <script>, <style>)."""
    blanked = HTML_SKIP_BLOCK.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)
    found = []
    for match in HTML_ATTR.finditer(blanked):
        if has_words(match.group(1)):
            found.append((blanked.count("\n", 0, match.start()) + 1, match.group(1)))
    for match in re.finditer(r">([^<>]*)<", blanked):
        if has_words(match.group(1)):
            found.append(
                (blanked.count("\n", 0, match.start()) + 1, match.group(1).strip())
            )
    return sorted(set(found))


def dictionary_keys(i18n_text):
    body = re.search(r"STRINGS\s*=\s*\{(.*?)\n\};", i18n_text, re.S)
    return (
        set(re.findall(r"^\s*([A-Za-z_]\w*)\s*:", body.group(1), re.M))
        if body
        else set()
    )


def key_findings(root, js_sources):
    """[(datoteka, vrstica, sporočilo)] za neznane in mrtve ključe slovarja."""
    i18n = Path(root) / "src" / "i18n.js"
    if not i18n.exists():
        return []
    known = dictionary_keys(i18n.read_text(encoding="utf-8"))
    used, findings, dynamic = set(), [], False
    for rel, text in js_sources.items():
        dynamic = dynamic or bool(DYNAMIC_T.search(text))
        for match in T_CALL.finditer(text):
            used.add(match.group(1))
            if match.group(1) not in known:
                line = text.count("\n", 0, match.start()) + 1
                findings.append(
                    (
                        rel,
                        line,
                        f't("{match.group(1)}"): ključa ni v STRINGS, izpiše se sam ključ',
                    )
                )
    if not dynamic:
        findings += [
            ("src/i18n.js", 1, f"ključ `{key}` ne bere nihče")
            for key in sorted(known - used)
        ]
    return findings


def find_all(root=None):
    """[(datoteka, vrstica, sporočilo)] — vse, kar je treba popraviti."""
    root = Path(root if root is not None else ROOT)
    findings, js_sources = [], {}
    for path in sorted((root / "src").rglob("*.js")):
        rel = path.relative_to(root).as_posix()
        if rel in SKIP:
            continue
        text = path.read_text(encoding="utf-8")
        js_sources[rel] = text
        findings += [
            (rel, n, f"besedilo mimo t(): {what[:60]!r}")
            for n, what in js_findings(text)
        ]
    html = root / "src" / "index.html"
    if html.exists():
        findings += [
            ("src/index.html", n, f"statično besedilo v HTML: {what[:60]!r}")
            for n, what in html_findings(html.read_text(encoding="utf-8"))
        ]
    findings += key_findings(root, js_sources)
    return sorted(findings)


def main(root=None):
    findings = find_all(root)
    for rel, number, message in findings:
        print(f"  {rel}:{number}  {message}")
    if len(findings) > BASELINE:
        print(
            f"\n  ✗ Besedila vmesnika: {len(findings)} nepravilnost(i). Vsako besedilo gre v src/i18n.js (STRINGS)\n"
            '    in se bere s t("ključ"); v HTML ga nastavi koda.'
        )
        return 1
    print(
        "  ✓ Besedila vmesnika: vse gre skozi t(), vsak ključ obstaja in ga kdo bere."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
