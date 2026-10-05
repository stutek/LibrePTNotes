"""`python -m agent_tools.css_tokens` — vsaka lastnost, ki jo CSS bere, je nekje zapisana, obe temi pa se ujemata.

Zakaj: `var(--ime)` brez definicije ne pade, ne opozori in ne izriše nič; CSS tiho vzame nadomestno
vrednost ob njem, to pa je barva, ki jo je nekdo vtipkal na dan pisanja, zato deklaracija neha
slediti temi in ostane na barvi avtorjeve teme. Slovar imen zato ni stvar spomina.

**Lastnost je definirana, kdor jo zapiše**, ne le stilski list:

    --ime: vrednost             kjerkoli v src/**/*.css
    setProperty("--ime", …)     v src/**/*.js (koda poda številko, ki jo ve samo izvajanje)
    style="--ime: …"            v oznakah ali predlogah

**Druga polovica je paritetna.** Temi sta svetla (`:root`) in temna (`prefers-color-scheme: dark`):
tema, ki lastnosti ne definira, jo podeduje od svetle, to pa je prav tista tiha napaka, ki se vidi
samo na telefonu v temnem načinu.

  * Barvna lastnost v temni, ki je ni v svetli, nima vrednosti v večini uporabnikov.
  * Barvna lastnost v svetli, ki je ni v temni, ostane svetla tudi v temni temi: izrecnost je smisel
    pariteta, tudi če sta barvi enaki (npr. `--primary`).
  * Nebarvne lastnosti (`env()`, dolžine, čas) nista temi in ju paritetni del ne zadeva.

**Dokumentirana izjema: kljuka kopije iz LibrePT.** `src/gesture/planPeek.css` bere `--peek-align`
z nadomestno vrednostjo (`var(--peek-align, 0px)`); v LibrePT jo zapiše pogled, ta aplikacija je ne
rabi, kopija pa mora ostati nespremenjena. Izjema velja samo za to datoteko in samo za branje z
nadomestno vrednostjo, ki je namen te kljuke (brez ujemanja se zapis pokaže od vrha).
"""

import re
import sys
from pathlib import Path

from agent_tools._tree import ROOT

USES = re.compile(r"var\(\s*(--[\w-]+)(\s*,)?")
DECLARATION = re.compile(r"(--[\w-]+)\s*:\s*([^;}]*)")
DEFINES_JS = re.compile(r"""setProperty\(\s*["'`](--[\w-]+)["'`]""")
DEFINES_INLINE = re.compile(r"""style\s*=\s*["'`][^"'`]*?(--[\w-]+)\s*:""")
OPTIONAL_HOOKS = {("src/gesture/planPeek.css", "--peek-align")}
COLOR_VALUE = re.compile(
    r"^(#[0-9a-fA-F]{3,8}|rgba?\(|hsla?\(|color-mix\(|var\()", re.I
)
DARK_MEDIA = re.compile(r"prefers-color-scheme\s*:\s*dark", re.I)
LIGHT_MEDIA = re.compile(r"prefers-color-scheme\s*:\s*light", re.I)


def blocks(css):
    """[(ovojni pogoji, izbirnik, telo)] za vsako pravilo z deklaracijami; @media se razgradi."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    found, stack, start = [], [], 0
    for i, char in enumerate(css):
        if char == "{":
            stack.append((css[start:i].strip(), i + 1))
            start = i + 1
        elif char == "}" and stack:
            head, body_start = stack.pop()
            body = css[body_start:i]
            if "{" not in body:
                found.append((tuple(h for h, _ in stack), head, body))
            start = i + 1
    return found


def theme_palettes(css):
    """({lastnost: vrednost} svetle teme, {…} temne) iz pravil `:root` stilskega lista."""
    light, dark = {}, {}
    for conditions, selector, body in blocks(css):
        if ":root" not in selector:
            continue
        target = dark if any(DARK_MEDIA.search(c) for c in conditions) else light
        if conditions and not any(
            DARK_MEDIA.search(c) or LIGHT_MEDIA.search(c) for c in conditions
        ):
            continue  # @media za nekaj drugega (zmanjšano gibanje …) ni tema
        target.update({n: v.strip() for n, v in DECLARATION.findall(body)})
    return light, dark


def parity_gaps(css):
    """[sporočilo] za barvne lastnosti, ki jih ima samo ena izmed obeh tem."""
    light, dark = theme_palettes(css)
    if not dark:
        return []
    gaps = []
    for name in sorted(set(dark) - set(light)):
        gaps.append(f"{name} je v temni temi, v svetli (`:root`) je ni")
    for name in sorted(set(light) - set(dark)):
        if COLOR_VALUE.match(light[name]):
            gaps.append(
                f"{name} je barva v svetli temi, v temni je ni (zapiši jo izrecno, tudi če je ista)"
            )
    return gaps


def sources(root, suffix):
    return sorted((Path(root) / "src").rglob(f"*{suffix}"))


def defined_tokens(root):
    names = set()
    for path in sources(root, ".css"):
        names.update(DECLARATION_NAME.findall(path.read_text(encoding="utf-8")))
    for suffix in (".js", ".html"):
        for path in sources(root, suffix):
            text = path.read_text(encoding="utf-8")
            names.update(DEFINES_JS.findall(text))
            names.update(DEFINES_INLINE.findall(text))
    return names


DECLARATION_NAME = re.compile(r"(--[\w-]+)\s*:")


def used_tokens(root):
    """{lastnost: [pot:vrstica, …]} za vsako branje `var(--…)` v stilskih listih."""
    uses = {}
    for path in sources(root, ".css"):
        rel = path.relative_to(root).as_posix()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for name, fallback in USES.findall(line):
                if fallback and (rel, name) in OPTIONAL_HOOKS:
                    continue
                uses.setdefault(name, []).append(f"{rel}:{number}")
    return uses


def find_all(root=None):
    """(neopredeljena branja [(kje, ime)], vrzeli v paritetnih [(datoteka, sporočilo)])."""
    root = Path(root if root is not None else ROOT)
    defined = defined_tokens(root)
    undefined = [
        (where, name)
        for name, wheres in sorted(used_tokens(root).items())
        if name not in defined
        for where in wheres
    ]
    gaps = []
    for path in sources(root, ".css"):
        rel = path.relative_to(root).as_posix()
        gaps += [(rel, g) for g in parity_gaps(path.read_text(encoding="utf-8"))]
    return undefined, gaps


def main(root=None):
    undefined, gaps = find_all(root)
    for where, name in undefined:
        print(f"  ✗ {where}  bere {name}, ki je nihče ne zapiše")
    for rel, gap in gaps:
        print(f"  ✗ {rel}  {gap}")
    if undefined or gaps:
        print(
            "\n  Nedoločena lastnost ne pade: CSS vzame nadomestno vrednost ob njej in neha slediti temi.\n"
            "  Poimenuj lastnost, ki jo aplikacija res definira, ali jo definiraj; barvi obeh tem sta izrecni."
        )
        return 1
    print(
        "  ✓ CSS lastnosti: vsaka prebrana je definirana, svetla in temna tema se ujemata."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
