"""`python -m agent_tools.inline_styles` — videz, zapisan v JavaScriptu ali HTML, namesto v CSS.

Pravilo (AGENT_RULES: videz samo v CSS): koda nastavlja razrede, ne `style`. Deklaracija na elementu
(`el.style.gap = …`, `style="color: …"`) premaga vsak stilski list, zato je tema ne more več
prekriti, in telefon v temnem načinu ostane s svetlo barvo, ki jo je nekdo zapisal v kodo.

**Ena dovoljena izjema:** `--plan-pull` v `src/gesture/planPeek.js` (kopija kretnje iz LibrePT:
poteg prsta je število, ki ga pozna samo izvajanje, CSS pa odloči, kaj naredi). Izjema je
imenovana po datoteki IN lastnosti; vsaka druga lastnost po `setProperty`, tudi samo
`--nekaj`, je kršitev, ker bi bila to že druga izjema brez zapisanega razloga.

Kaj se išče: prireditev `.style.x = …` / `.style["x"] = …` / `.style.cssText = …`,
`.style.setProperty(…)` ter atribut `style="…"` v JS in v `src/index.html`. Generirane strani
dokumentov (`privacy.html`) se ne iščejo: nimajo aplikacijskega CSS, ime strani ni v tej poti.
"""

import re
import sys
from pathlib import Path

from agent_tools._tree import ROOT

ALLOWED = {("src/gesture/planPeek.js", "--plan-pull")}

ASSIGNED = re.compile(r"\.style(?:\.[A-Za-z]+|\[[^\]]+\])\s*=(?!=)")
SET_PROPERTY = re.compile(r"""\.style\.setProperty\(\s*(["'`])([^"'`]*)\1""")
STYLE_ATTRIBUTE = re.compile(r"""\sstyle\s*=\s*\\?(["'])(.*?)\\?\1""", re.S)
SET_ATTRIBUTE_STYLE = re.compile(r"""setAttribute\(\s*["']style["']""")


def findings_in(rel, text):
    """[(vrstica, vrstica izvora)] za vsak slog, ki ga stilski list ne more prekriti."""
    offsets = [m.start() for m in ASSIGNED.finditer(text)]
    offsets += [m.start() for m in SET_ATTRIBUTE_STYLE.finditer(text)]
    offsets += [
        m.start()
        for m in SET_PROPERTY.finditer(text)
        if (rel, m.group(2)) not in ALLOWED
    ]
    offsets += [m.start() for m in STYLE_ATTRIBUTE.finditer(text) if m.group(2).strip()]
    lines = text.splitlines()
    return [
        (n, lines[n - 1].strip())
        for n in sorted({text.count("\n", 0, o) + 1 for o in offsets})
    ]


def find_all(root=None):
    root = Path(root if root is not None else ROOT)
    sources = sorted((root / "src").rglob("*.js")) + [root / "src" / "index.html"]
    found = []
    for path in sources:
        if path.exists():
            rel = path.relative_to(root).as_posix()
            found += [
                (rel, n, line)
                for n, line in findings_in(rel, path.read_text(encoding="utf-8"))
            ]
    return found


def main(root=None):
    found = find_all(root)
    for rel, number, line in found:
        print(f"  {rel}:{number}  {line[:120]}")
    if found:
        print(
            f"\n  ✗ Slogi v kodi: {len(found)}. Elementu daj razred ali atribut stanja in zapiši deklaracijo v CSS;\n"
            "    edina izjema je `--plan-pull` v src/gesture/planPeek.js."
        )
        return 1
    print("  ✓ Slogi v kodi: ni jih (izjema: --plan-pull v kretnji).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
