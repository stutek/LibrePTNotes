"""`python -m agent_tools.use_case_tests` — vsak primer uporabe pove, kateri test drži katero obljubo.

Primer uporabe v `use_cases/` je specifikacija, po kateri je zgrajeno trenerjevo delo. Obljuba,
za katero nihče ne odgovarja s testom, je obljuba, ki je nihče ne primerja z aplikacijo; v LibrePT
so štirje primeri brez tabele bili prav tisti, kjer se je specifikacija najbolj oddaljila od
aplikacije (opisovali so gumbe, ki jih ni).

**Kaj zahteva.** Vsak `use_cases/uc*.md` ima naslov, ki vsebuje »sledljivost« (ali »traceability«),
in pod njim tabelo. Zadnja celica vsake vrstice je bodisi povezava v `tests/`, bodisi se začne z
**Ni zgrajeno** / **Zunaj aplikacije** in pove zakaj, da je obljuba brez testa še vedno zapisana
kot taka. Ali povezave kažejo na obstoječe datoteke, preverja doclinks.
"""

import re
import sys
from pathlib import Path

from agent_tools._tree import ROOT

NO_TEST = ("**Ni zgrajeno**", "**Zunaj aplikacije**")
HEADING = re.compile(r"^#{2,6} .*(?:sledljivost|traceability)", re.I)
TEST_LINK = re.compile(r"\]\((?:\.\./)?tests/")


def table_rows(lines):
    """Vrstice prve tabele pod naslovom sledljivosti (brez glave in ločila); None, če naslova ni."""
    start = next((i for i, line in enumerate(lines) if HEADING.match(line)), None)
    if start is None:
        return None
    rows = []
    for line in lines[start + 1 :]:
        if line.startswith("|"):
            rows.append(line)
        elif rows:
            break
    return rows[2:]


def last_cell(row):
    cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
    return cells[-1] if cells else ""


def problems_in(text):
    """Kaj je narobe pri enem primeru uporabe, kot stavki; prazno, če nič."""
    rows = table_rows(text.splitlines())
    if rows is None:
        return ["nima naslova o sledljivosti"]
    if not rows:
        return ["ima naslov o sledljivosti in pod njim nobene vrstice tabele"]
    return [
        f"vrstica ne navaja ne testa ne razloga: {row.strip()[:100]}"
        for row in rows
        if not (TEST_LINK.search(last_cell(row)) or last_cell(row).startswith(NO_TEST))
    ]


def find_all(root=None):
    root = Path(root if root is not None else ROOT)
    cases = sorted((root / "use_cases").glob("uc*.md"))
    found = [
        (p.relative_to(root).as_posix(), problem)
        for p in cases
        for problem in problems_in(p.read_text(encoding="utf-8"))
    ]
    if not cases:
        found.append(("use_cases/", "ni nobenega primera uporabe (uc*.md)"))
    return found


def main(root=None):
    found = find_all(root)
    for rel, problem in found:
        print(f"  ✗ {rel}: {problem}")
    if found:
        print(
            "\n  Vsak primer uporabe se konča s tabelo: vsaka vrstica povezuje test, ki drži obljubo,\n"
            f"  ali se začne z {' / '.join(NO_TEST)} in pove zakaj."
        )
        return 1
    print("  ✓ Vsak primer uporabe kaže z vsako obljubo na test ali pove, zakaj ga ni.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
