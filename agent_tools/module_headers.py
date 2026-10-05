"""`python -m agent_tools.module_headers` — modul, ki v prvi vrstici imenuje svojo pot, jo imenuje prav.

Zakaj: prva vrstica modula je njegova samodokumentacija (`// src/domain/notes.js — opis`); bralec
ali agent, ki išče datoteko, ji zaupa. Ob premiku datoteke postane napačna, in prav ob premiku nihče
ne pogleda vrstice 1: napačna pot ne le ne pomaga, ampak vodi v mapo, ki je ni več.

Kaj se preverja in kaj ne:

  * Prva vrstica, ki se ZAČNE s potjo (`// pot/do/datoteke.js …`), trdi, kje modul živi, in trditev
    mora držati (pot z `src/`).
  * Prva vrstica s prozo trditve ne daje in se pusti pri miru; zahtevati pot povsod bi bilo drugo,
    bolj dolgočasno pravilo, ki ne prinese nič.
  * **Dokumentirana izjema: kopija iz LibrePT.** `src/gesture/planPeek.js` je kopija, ki mora
    ostati nespremenjena; njena prva vrstica pravi »// Kopija iz LibrePT: …« (proza, torej brez
    trditve), druga vrstica pa nosi LibrePT-jevo pot `src/modules/clipboard/planPeek.js`. Preverja
    se samo prva vrstica, zato kopija brez posebnega seznama izjem prestane; oznaka »Kopija iz
    LibrePT« je tudi izrecno priznana, da bi izjema ostala, če bi kdo prvo vrstico preoblikoval.

Izpiše samo kršitve; popravek je ročen (`--fix` ni, ker bi ugibal opis za potjo).
"""

import re
import sys
from pathlib import Path

from agent_tools._tree import ROOT

# Prvi simbol uvodnega komentarja, če je videti kot pot do .js: samo samotrditev, nikoli omemba
# sosednjega modula nekje v vrstici.
SELF_PATH = re.compile(r"^//\s*([\w./-]+\.js)(?=\s|$)")
COPY_MARK = re.compile(r"^//\s*Kopija iz LibrePT\b")


def claimed_path(source_text):
    """Pot, ki jo modul v prvi vrstici trdi za svojo, ali None (proza ali oznaka kopije)."""
    first = source_text.split("\n", 1)[0]
    if COPY_MARK.match(first):
        return None
    match = SELF_PATH.match(first)
    return match.group(1) if match else None


def wrong_headers(root=None):
    """[(dejanska pot, trdena pot)] za vsak modul pod src/, katerega trditev ne drži."""
    root = Path(root if root is not None else ROOT)
    wrong = []
    for path in sorted((root / "src").rglob("*.js")):
        actual = path.relative_to(root).as_posix()
        claimed = claimed_path(path.read_text(encoding="utf-8"))
        if claimed is not None and claimed != actual:
            wrong.append((actual, claimed))
    return wrong


def main(root=None):
    wrong = wrong_headers(root)
    for actual, claimed in wrong:
        print(f"  ✗ {actual}:1  prva vrstica pravi, da je {claimed}")
    if wrong:
        print(f"  ✗ Glave modulov: {len(wrong)} modul(ov) imenuje pot, ki ni njihova.")
        return 1
    print("  ✓ Glave modulov: vsaka samoimenovana pot ustreza datoteki.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
