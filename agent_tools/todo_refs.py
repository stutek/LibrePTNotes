"""`python -m agent_tools.todo_refs` — nobena datoteka razen TODO.md ne kaže na njegove razdelke.

Zakaj: razdelek TODO se zapre, preštevilči ali premakne, komentar `TODO.md §2` pa kaže na besedilo,
ki ne ostane tam, kjer je bilo; bralec, ki mu sledi, najde nekaj drugega ali nič. Zato datoteka
zapiše svoj razlog sama. TODO.md smeš imenovati kot dom odprtega dela, njegovega razdelka ne.

Kaj je kršitev v vsaki datoteki repozitorija razen izjem spodaj:

  1. Kazalec, ki imenuje TODO: `TODO §2`, `TODO.md §3`, `TODO.md section 2` ali povezava na
     `TODO.md#…`.
  2. V vsem, kar ni markdown (koda, testi, orodja, CSS): golo `§N` brez imenovanega dokumenta.
     V kodi je goli znak § vedno pomenil TODO. `DATA_MODEL §1` ali `RFC 6350 §3` dokument imenujeta.
  3. V markdownu: golo `§N`, ki ga ta dokument nima kot svoj oštevilčeni razdelek; kazal je torej
     drugam, v praksi v TODO.

Izjeme: TODO.md sam; AGENT_RULES.md, ki zapiše, kje se odločitve beležijo; in orodja z njihovimi
testi, ki zapis kazalca vsebujejo kot primer kršitve.
"""

import re
import sys

from agent_tools._tree import ROOT, read, repo_files
from agent_tools.doclinks import parse_structure, strip_code

EXEMPT = {
    "TODO.md",
    "AGENT_RULES.md",
    "agent_tools/doclinks.py",
    "agent_tools/todo_hygiene.py",
    "agent_tools/todo_refs.py",
    "tests/unit/test_agent_tools_doclinks.py",
    "tests/unit/test_agent_tools_todo_hygiene.py",
    "tests/unit/test_agent_tools_todo_refs.py",
}
TEXT_SUFFIXES = {
    ".md",
    ".js",
    ".mjs",
    ".css",
    ".html",
    ".py",
    ".yml",
    ".yaml",
    ".json",
    ".txt",
    ".toml",
    ".webmanifest",
}

NAMES_TODO = re.compile(r"TODO(?:\.md)?,? ?§|TODO\.md#|TODO(?:\.md)? section \d")
SECTION = re.compile(r"§ ?(\d+)")
# Kar pred § imenuje dokument: VELIKE_ČRKE (DATA_MODEL, UC6), pot do .md ali RFC s številko.
QUALIFIER = re.compile(r"(?:\b[A-Z][A-Z0-9_]+|[\w./-]+\.md|RFC \d+)[,:]? ?$")
CONTINUATION = re.compile(r"§ ?[\d.]+ ?(?:/|,|and|or|in) ?$")


def bare_sections(line):
    """Številke vseh `§N` v vrstici, ki ne imenujejo dokumenta."""
    bare, qualified_before = [], False
    for match in SECTION.finditer(line):
        before = line[: match.start()]
        if QUALIFIER.search(before) and not before.rstrip().endswith("TODO"):
            qualified_before = True
        elif not (qualified_before and CONTINUATION.search(before)):
            bare.append(match.group(1))
            qualified_before = False
    return bare


def findings_in(rel, text):
    """[(vrstica, besedilo)] za vsak kazalec na TODO v `text`, prebranem kot datoteka `rel`."""
    markdown = rel.endswith(".md")
    if markdown:
        text = strip_code(text)
        own = {n.split(".")[0] for n in parse_structure(text)[1]}
    else:
        own = set()
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        points_away = [n for n in bare_sections(line) if n not in own]
        if NAMES_TODO.search(line) or points_away:
            found.append((number, line.strip()))
    return found


def find_all(root=None):
    root = root if root is not None else ROOT
    found = []
    for rel in repo_files(root):
        if rel in EXEMPT or not any(rel.endswith(s) for s in TEXT_SUFFIXES):
            continue
        try:
            text = read(root, rel)
        except UnicodeDecodeError:
            continue
        found += [(rel, n, line) for n, line in findings_in(rel, text)]
    return found


def main(root=None):
    found = find_all(root)
    if found:
        print(f"\n  ✗ Kazalci na TODO: {len(found)} vrstic kaže v TODO.md\n")
        for rel, number, line in found:
            print(f"    {rel}:{number}  {line[:120]}")
        print(
            "\n    Razdelek TODO se zapre in besedilo se premakne. Razlog zapiši tja, kjer ga rabiš."
        )
        return 1
    print(
        "  ✓ Kazalci na TODO: nobena datoteka razen TODO.md ne kaže na njegove razdelke."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
