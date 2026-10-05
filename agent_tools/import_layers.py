"""`python -m agent_tools.import_layers` — uvozi tečejo samo navzgor po slojih in vsak uvoz obstaja.

Zakaj: aplikacija je zgrajena na tem, da je vsak sloj preizkusljiv sam (domain v Nodu brez vsega,
data z pomnilniškim backendom, ui z lažnim DOM). Ena `import` vrstica v napačno smer to tiho
odstrani: modul še dela, nič ne pade, in naslednji, ki ga hoče preizkusiti, odkrije, da vleče s
sabo pol aplikacije.

Sloji, od spodaj navzgor; vsak sme uvoziti samo iz sebe in iz nižjih:

    domain/     čista pravila; brez DOM, brez shrambe, brez data/ in ui/
    data/       shramba in kopija; sme domain/
    ui/         izris; sme domain/ in data/ (besedila dobi s `t` kot argument, ne uvozi i18n.js)
    app.js      sestavljalec; sme vse

Samostojni listi:

    gesture/    kretnja L (kopija iz LibrePT): ne uvozi iz nobenega drugega sloja, uvozi jo ui/ ali app.js
    i18n.js     slovar: ne uvozi nič; sme ga uvoziti samo app.js (ui/ dobi `t` z injekcijo)
    sw.js       service worker: nima uvozov (teče v svojem kontekstu, brez modulov)

Dodatno: `domain/` ne sme segati po brskalniškem okolju (`document`, `window`, `navigator`,
`localStorage`, `indexedDB`); čistost je pogoj, da ga Node preizkusi brez lažnih objektov.
Vsak relativni uvoz mora kazati na obstoječo datoteko: premik datoteke pusti uvoz v prazno, Node pa
javi napako šele ob zagonu.
"""

import re
import sys
from pathlib import Path

from agent_tools._tree import ROOT

LAYERS = {"domain": 0, "data": 1, "ui": 2}
ROOT_APP = "src/app.js"
LEAVES = {"src/i18n.js", "src/sw.js"}
BROWSER_GLOBALS = re.compile(
    r"\b(document|window|navigator|localStorage|sessionStorage|indexedDB)\b"
)
STATIC_IMPORT = re.compile(
    r"""^\s*import\s[^'"]*?['"]([^'"]+)['"]|^\s*export\s[^'"]*?\sfrom\s*['"]([^'"]+)['"]""",
    re.M,
)
DYNAMIC_IMPORT = re.compile(r"""\bimport\(\s*['"]([^'"]+)['"]\s*\)""")
IMPORT_SCRIPTS = re.compile(r"\bimportScripts\(")


def strip_comments(text):
    """Komentarji so prazni (vrstice ostanejo): omemba `document` v komentarju ni dostop do DOM."""
    return re.sub(
        r"/\*.*?\*/|(?<![:\"'])//[^\n]*",
        lambda m: re.sub(r"[^\n]", " ", m.group(0)),
        text,
        flags=re.S,
    )


def specifiers(text):
    static = [a or b for a, b in STATIC_IMPORT.findall(text)]
    return static + DYNAMIC_IMPORT.findall(text)


def layer_of(rel):
    """`domain`, `data`, `ui`, `gesture`, `app`, `i18n`, `sw` ali None (zunaj teh)."""
    if rel == ROOT_APP:
        return "app"
    if rel == "src/i18n.js":
        return "i18n"
    if rel == "src/sw.js":
        return "sw"
    parts = rel.split("/")
    if len(parts) >= 3 and parts[0] == "src" and parts[1] in (*LAYERS, "gesture"):
        return parts[1]
    return None


def allowed(importer, imported):
    """Sme modul iz sloja `importer` uvoziti modul iz sloja `imported`?"""
    if importer == "app":
        return True
    if importer in ("sw", "i18n"):
        return False
    if importer == "gesture":
        return imported == "gesture"
    if imported == "gesture":
        return importer == "ui"
    if imported in ("i18n", "app", "sw"):
        return False
    return LAYERS[imported] <= LAYERS[importer]


def find_all(root=None):
    """[(datoteka, vrstica, sporočilo)] za nedovoljene uvoze, manjkajoče uvoze in nečist domain."""
    root = Path(root if root is not None else ROOT)
    found = []
    for path in sorted((root / "src").rglob("*.js")):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        importer = layer_of(rel)
        if importer == "sw" and IMPORT_SCRIPTS.search(text):
            found.append(
                (rel, 1, "service worker ne sme nalagati skript (importScripts)")
            )
        if importer == "domain":
            clean = strip_comments(text)
            for match in BROWSER_GLOBALS.finditer(clean):
                line = clean.count("\n", 0, match.start()) + 1
                found.append(
                    (rel, line, f"domain mora biti čist, pa rabi `{match.group(1)}`")
                )
        for specifier in specifiers(text):
            if not specifier.startswith("."):
                found.append(
                    (
                        rel,
                        1,
                        f"uvoz '{specifier}' ni relativen (brez knjižnic in URL-jev)",
                    )
                )
                continue
            target = (path.parent / specifier).resolve()
            if not target.exists():
                found.append((rel, 1, f"uvoz '{specifier}' ne kaže na nobeno datoteko"))
                continue
            try:
                imported = layer_of(target.relative_to(root.resolve()).as_posix())
            except ValueError:
                found.append((rel, 1, f"uvoz '{specifier}' zapusti repozitorij"))
                continue
            if importer and imported and not allowed(importer, imported):
                found.append(
                    (
                        rel,
                        1,
                        f"{importer} uvaža {imported} ('{specifier}'): sloj ne sme segati tja",
                    )
                )
    return found


def main(root=None):
    found = find_all(root)
    for rel, number, message in found:
        print(f"  ✗ {rel}:{number}  {message}")
    if found:
        print(
            f"\n  ✗ Sloji uvozov: {len(found)} kršitev. Odvisnost podaj kot argument, ne uvozi je navzgor;\n"
            "    uvoz v napačno smer odvzame modulu preizkusljivost samega zase."
        )
        return 1
    print(
        "  ✓ Sloji uvozov: domain < data < ui < app, kretnja samostojna, vsak uvoz obstaja."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
