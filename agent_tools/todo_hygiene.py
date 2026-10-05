"""`python -m agent_tools.todo_hygiene` — TODO.md ostane en sam vir resnice in ostane kratek.

Zakaj: TODO.md je specifikacija, odločitve in odprto delo hkrati (en vir resnice), zato ga prebere
vsak agent ob vsaki seji. Zaprta točka, ki ohrani celo razpravo, to ceno plačuje v neskončnost, in
nič ne pade, ko jo kdo pozabi pospraviti. LibrePT to reši z arhivom; tu arhiva ni (repo je majhen),
zato velja ista misel v manjši obliki: **zaprta točka (`- [x]`) v §3 je ena vrstica z izidom**, razlog
pa je že v §2 (odločitve), kjer ga najdeš z razlogom vred.

Kontrole (čista analiza datotek):

  1. Razdelki `## N.` so oštevilčeni od 1 naprej brez vrzeli in ponovitev, da `§N` vedno kaže na
     eno samo mesto.
  2. Vsaka točka najvišje ravni v §3 je `- [ ]` ali `- [x]`; vse drugo (`[X]`, `[~]`, golo `-`) je
     točka, o kateri ni jasno, ali je odprta.
  3. Zaprta točka je ena vrstica, dolga največ `MAX_CLOSED_CHARS` znakov, brez nadaljevanja.
"""

import re
import sys
from pathlib import Path

from agent_tools._tree import ROOT

OPEN_SECTION = 3
MAX_CLOSED_CHARS = 240

SECTION = re.compile(r"^## (\d+)\.\s")
BULLET = re.compile(r"^- (.*)$")
BOX = re.compile(r"^\[( |x)\] ")


def section_bodies(lines):
    """[(številka razdelka, vrstica naslova (od 1), vrstice pod njim)] za `## N.` naslove."""
    heads = [
        (i, int(m.group(1)))
        for i, line in enumerate(lines)
        if (m := SECTION.match(line))
    ]
    ends = [i for i, _ in heads[1:]] + [len(lines)]
    return [(num, i + 1, lines[i + 1 : end]) for (i, num), end in zip(heads, ends)]


def check_numbering(sections):
    findings, expected = [], 1
    for number, line_no, _ in sections:
        if number != expected:
            findings.append(
                (
                    line_no,
                    f"razdelek {number}, pričakovan {expected}: številčenje mora biti 1, 2, 3 …",
                )
            )
        expected = number + 1
    return findings


def check_open_section(line_no, body):
    """Točke najvišje ravni v §3: oblika polja in dolžina zaprtih."""
    findings, bullets = [], []
    for offset, line in enumerate(body):
        at = line_no + 1 + offset
        if BULLET.match(line):
            bullets.append([at, line, 0])
        elif bullets and line.strip():
            bullets[-1][2] += 1  # nadaljevalna vrstica
    for at, line, continuation in bullets:
        text = BULLET.match(line).group(1)
        box = BOX.match(text)
        if not box:
            findings.append(
                (at, "točka v §3 nima `[ ]` ali `[x]`: ni jasno, ali je odprta")
            )
        elif box.group(1) == "x" and (continuation or len(line) > MAX_CLOSED_CHARS):
            findings.append(
                (
                    at,
                    f"zaprta točka je daljša od ene vrstice ({MAX_CLOSED_CHARS} znakov): razlog sodi v §2, tu ostane izid",
                )
            )
    return findings


def find_all(root=None):
    """[("TODO.md", vrstica, sporočilo)]."""
    path = Path(root if root is not None else ROOT) / "TODO.md"
    if not path.exists():
        return [("TODO.md", 1, "datoteke ni")]
    sections = section_bodies(path.read_text(encoding="utf-8").splitlines())
    findings = check_numbering(sections)
    for number, line_no, body in sections:
        if number == OPEN_SECTION:
            findings += check_open_section(line_no, body)
    if not any(n == OPEN_SECTION for n, _, _ in sections):
        findings.append((1, f"manjka razdelek §{OPEN_SECTION} (odprto delo)"))
    return [("TODO.md", at, message) for at, message in sorted(findings)]


def main(root=None):
    findings = find_all(root)
    for rel, at, message in findings:
        print(f"  {rel}:{at}  {message}")
    if findings:
        print(
            f"\n  ✗ TODO: {len(findings)} nepravilnost(i); zaprto delo ne sme bremeniti vsakega bralca."
        )
        return 1
    print("  ✓ TODO: razdelki so oštevilčeni in zaprte točke v §3 so kratke.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
