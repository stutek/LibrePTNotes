"""`python -m agent_tools.catalog_coverage` — katalog modulov res opisuje module.

Zakaj: `docs/modules.md` je zemljevid kode in zastara tiho: povezave v njem ostanejo zelene (doclinks
preverja, da kažejo na obstoječe datoteke), modul, ki ga nihče ni vpisal, pa v zemljevidu ne obstaja.
Agent, ki zemljevidu zaupa, potem sklepa iz različice repozitorija, ki je ni več. LibrePT je ob prvem
zagonu našel 22 modulov brez vpisa.

Dve smeri, ker ena sama pušča pol zemljevida:

  1. **Pokritost** — vsak `.js`, `.css` in `.html` pod `src/` je v katalogu.
  2. **Zastarelost** — vsaka pot `src/…` v katalogu, ki se konča z eno od teh pripon, še obstaja.

Katalog je v `docs/`, ne v `src/`: v `src/` je samo tisto, kar se objavi in predpomni.
Vsak vpis je ena vrstica, povezava `[src/pot](../src/pot) — opis`; opis ne sme biti prazen.
"""

import re
import sys
from pathlib import Path

from agent_tools._tree import ROOT

CATALOG = "docs/modules.md"
SUFFIXES = (".js", ".css", ".html")
SRC_LINK = re.compile(r"\]\(\.\./(src/[^)#]+)\)(.*)")


def catalogued(text):
    """{pot: opis} za vsak vpis v katalogu; opis je besedilo za povezavo brez ločil."""
    return {
        m.group(1): m.group(2).strip(" —-–:")
        for m in map(SRC_LINK.search, text.splitlines())
        if m
    }


def runtime_modules(root):
    src = Path(root) / "src"
    return {
        p.relative_to(root).as_posix()
        for p in src.rglob("*")
        if p.is_file() and p.suffix in SUFFIXES
    }


def find_all(root=None):
    """(manjkajoči, zastareli, brez opisa) — vsak kot urejen seznam poti."""
    root = Path(root if root is not None else ROOT)
    listed = catalogued((root / CATALOG).read_text(encoding="utf-8"))
    actual = runtime_modules(root)
    missing = sorted(actual - set(listed))
    stale = sorted(p for p in set(listed) - actual if p.endswith(SUFFIXES))
    blank = sorted(
        p for p, description in listed.items() if p in actual and not description
    )
    return missing, stale, blank


def main(root=None):
    root = Path(root if root is not None else ROOT)
    if not (root / CATALOG).exists():
        print(f"  ✗ Kataloga ni: {CATALOG}")
        return 1
    missing, stale, blank = find_all(root)
    for path in missing:
        print(f"  ✗ {path} ni v {CATALOG}")
    for path in stale:
        print(f"  ✗ {CATALOG} našteva {path}, ki ga ni več")
    for path in blank:
        print(f"  ✗ {CATALOG}: {path} nima opisa")
    if missing or stale or blank:
        print(
            f"  ✗ Katalog modulov: {len(missing)} manjka, {len(stale)} zastarelih, {len(blank)} brez opisa."
        )
        return 1
    print(
        f"  ✓ Katalog modulov: vseh {len(runtime_modules(root))} modulov je vpisanih z opisom."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
