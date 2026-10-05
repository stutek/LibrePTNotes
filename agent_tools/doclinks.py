"""`python -m agent_tools.doclinks` — kazalo, frontmatter in povezave med markdown datotekami.

Zakaj: agenti po povezavah iščejo kontekst. Preimenovana datoteka ali razdelek pusti mrtvo
povezavo, ki še vedno izgleda pravilno; sledi ji šele naslednji agent, v prazno. Tu je to pravilo
strojno preverjeno.

Kontrole (čista analiza datotek, brez omrežja):

  1. **Frontmatter** — vsaka `.md` ima `type`, `title`, `description` in `tags` z vsebino.
     Izjema so le tri datoteke, ki jih agent nalaga ob prihodu (CLAUDE.md, AGENTS.md, GEMINI.md):
     frontmatter bi se vpisal v kontekst vsakega agenta.
  2. **Kazalo** — vsaka `.md` je povezana iz `index.md`; datoteka, ki je ni v kazalu, je za agenta
     neobstoječa.
  3. **Povezave** — vsaka relativna `[besedilo](pot)` kaže na obstoječo datoteko, vsako `#sidro`
     na obstoječ naslov (pravila GitHub).
  4. **Razdelki** — `§N` kaže na oštevilčen naslov. Brez imenovanega dokumenta velja za ta
     dokument; `§N točka M` zahteva, da je v razdelku N oštevilčena točka M (specifikacija v
     TODO.md §1 se sklicuje na točke, številčenje pa se ob urejanju premakne).

Primeri v kodnih blokih in vrstični kodi so primeri, ne povezave.
"""

import difflib
import re
import sys
from pathlib import Path

from agent_tools._tree import ROOT, read, repo_files

LOADERS = {"CLAUDE.md", "AGENTS.md", "GEMINI.md"}
REQUIRED_KEYS = ("type", "title", "description", "tags")

EXTERNAL = re.compile(r"^(https?:|mailto:|tel:|data:|//)")
MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")
NUMBERED_HEADING = re.compile(r"^(\d+(?:\.\d+)*)\s*[.:)]?\s")
ORDERED_ITEM = re.compile(r"^(\d+)[.)]\s")
SECTION_REF = re.compile(r"§\s*(\d+(?:\.\d+)*)(?:\s+točk[aei]\s+(\d+))?")
# Dokument, ki ga § imenuje: `TODO.md §2`, `[TODO.md](TODO.md) §2` ali golo ime `TODO §2`.
QUALIFIER = re.compile(r"([\w./-]+\.md|\b[A-Z][A-Z0-9_]+)[\s,:]*$")
LINK_REACH = 4


def slugify(heading):
    """Sidro po pravilih GitHub: male črke, brez oblikovanja in ločil, presledki v vezaje."""
    text = re.sub(r"<[^>]+>", "", heading)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[`*~]", "", text).strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return normalize(re.sub(r"\s", "-", text))


def normalize(fragment):
    """Zložene vezaje primerjamo kot enega: preveri se, ali razdelek obstaja, ne štetje vezajev."""
    return re.sub(r"-{2,}", "-", fragment.lower())


def split_frontmatter(text):
    """(slovar ključev, telo). Brez frontmatterja je slovar prazen in telo celo besedilo."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    keys = {}
    for line in text[4:end].splitlines():
        match = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys, text[end + 4 :]


def _inline_code(match):
    """Ime md datoteke v vrstični kodi ostane (`TODO.md` §2 imenuje dokument); drugo je primer."""
    inner = match.group(1)
    return inner if re.fullmatch(r"[\w./-]+\.md", inner) else ""


def strip_code(text):
    """Prazno namesto kodnih blokov in vrstične kode; številčenje vrstic ostane."""
    out, in_fence = [], False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            out.append("")
        else:
            out.append("" if in_fence else re.sub(r"`([^`]*)`", _inline_code, line))
    return "\n".join(out)


def parse_structure(text):
    """(sidra, številke razdelkov, točke »N.M«) — kar je v kodnem bloku, se ne šteje."""
    anchors, sections, items, seen = set(), set(), set(), {}
    current = None
    for line in strip_code(text).splitlines():
        heading = HEADING.match(line)
        if heading:
            slug = slugify(heading.group(2))
            count = seen.get(slug, 0)
            seen[slug] = count + 1
            anchors.add(slug)
            if count:
                anchors.add(normalize(f"{slug}-{count}"))
            number = NUMBERED_HEADING.match(heading.group(2))
            current = number.group(1) if number else None
            if number:
                sections.add(current)
            continue
        item = ORDERED_ITEM.match(line)
        if item and current:
            items.add(f"{current}.{item.group(1)}")
    return anchors, sections, items


class Docs:
    """Berljivi markdown dokumenti drevesa, razčlenjeni enkrat."""

    def __init__(self, root):
        self.root = Path(root)
        self.files = [f for f in repo_files(self.root) if f.endswith(".md")]
        self.text = {f: read(self.root, f) for f in self.files}
        self._structure = {}

    def structure(self, rel):
        if rel not in self._structure:
            self._structure[rel] = parse_structure(self.text[rel])
        return self._structure[rel]

    def resolve(self, source, target):
        """Repo-relativna pot, na katero kaže povezava iz `source`, ali None, če zapusti repo."""
        path = (self.root / source).parent / target
        try:
            return path.resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return None


def check_frontmatter(docs):
    findings = []
    for rel in docs.files:
        if rel in LOADERS:
            continue
        keys, _ = split_frontmatter(docs.text[rel])
        if not keys:
            findings.append(
                (rel, 1, "manjka frontmatter (type, title, description, tags)")
            )
            continue
        for key in REQUIRED_KEYS:
            if keys.get(key, "") in ("", "[]", '""', "''"):
                findings.append((rel, 1, f"frontmatter nima vrednosti `{key}`"))
    return findings


def check_index(docs):
    if "index.md" not in docs.files:
        return [("index.md", 1, "kazala ni")]
    listed = set()
    for _, target in re.findall(MD_LINK, strip_code(docs.text["index.md"])):
        if not EXTERNAL.match(target):
            resolved = docs.resolve("index.md", target.partition("#")[0])
            if resolved:
                listed.add(resolved)
    return [
        (rel, 1, "ni vpisana v index.md")
        for rel in docs.files
        if rel != "index.md" and rel not in LOADERS and rel not in listed
    ]


def nearest(fragment, anchors):
    close = difflib.get_close_matches(fragment, sorted(anchors), n=1, cutoff=0.75)
    return close[0] if close else None


def check_links(docs, rel, number, line):
    findings = []
    for _label, target in MD_LINK.findall(line):
        if EXTERNAL.match(target):
            continue
        file_part, _, fragment = target.partition("#")
        resolved = docs.resolve(rel, file_part) if file_part else rel
        if resolved is None or not (docs.root / resolved).exists():
            findings.append((rel, number, f"mrtva povezava → {file_part}"))
        elif fragment and resolved.endswith(".md"):
            anchors = docs.structure(resolved)[0]
            if normalize(fragment) not in anchors:
                near = nearest(normalize(fragment), anchors)
                hint = f" (misliš #{near}?)" if near else ""
                findings.append((rel, number, f"mrtvo sidro → #{fragment}{hint}"))
    return findings


def qualifier_target(docs, rel, line, start):
    """Dokument, ki ga § na tem mestu imenuje: imenovan dokument ali (brez imena) ta dokument.
    None pomeni »imenovan dokument, ki ga ne poznamo« (npr. RFC), kar se ne preverja."""
    for match in MD_LINK.finditer(line):
        inside = match.start() < start < match.start(1) + len(match.group(1))
        just_before = 0 <= start - match.end() <= LINK_REACH
        if inside or just_before:
            target = match.group(2).partition("#")[0]
            resolved = docs.resolve(rel, target) if target else rel
            if resolved in docs.files:
                return resolved
    named = QUALIFIER.search(line[:start])
    if not named:
        return rel
    name = named.group(1)
    stem = name[:-3] if name.endswith(".md") else name
    for candidate in docs.files:
        if Path(candidate).stem == stem or candidate == name:
            return candidate
    return None


def check_sections(docs, rel, number, line):
    findings = []
    for match in SECTION_REF.finditer(line):
        target = qualifier_target(docs, rel, line, match.start())
        if target is None:
            continue
        _, sections, items = docs.structure(target)
        section, item = match.group(1), match.group(2)
        where = "" if target == rel else f"{target} "
        exists = section in sections or any(
            s.startswith(section + ".") for s in sections
        )
        if not exists:
            findings.append((rel, number, f"viseča pot → {where}§{section}"))
        elif item and f"{section}.{item}" not in items:
            findings.append(
                (rel, number, f"viseča pot → {where}§{section} točka {item}")
            )
    return findings


def find_all(root=None):
    docs = Docs(root if root is not None else ROOT)
    findings = check_frontmatter(docs) + check_index(docs)
    for rel in docs.files:
        for number, line in enumerate(strip_code(docs.text[rel]).splitlines(), 1):
            findings += check_links(docs, rel, number, line)
            findings += check_sections(docs, rel, number, line)
    return sorted(findings, key=lambda f: (f[0], f[1], f[2])), len(docs.files)


def main(root=None):
    findings, count = find_all(root)
    if findings:
        print(f"\n  ✗ Dokumenti: {len(findings)} nepravilnost(i)\n")
        for rel, number, message in findings:
            print(f"    {rel}:{number}  {message}")
        print(
            "\n    Popravi povezavo ali naslov: mrtva povezava je slepa ulica za naslednjega agenta."
        )
        return 1
    print(
        f"  ✓ Dokumenti: {count} md datotek, frontmatter, kazalo, povezave in razdelki so v redu."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
