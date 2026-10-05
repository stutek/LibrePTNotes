"""Ena deklaracija različice Pythona in ta računalnik na njej.

**Zakaj.** CI in lastnikov računalnik lahko tečeta na različnih različicah jezika, pa nič v repozitoriju
tega ne pove; »pri meni dela« potem sploh ni več o testih. Najdražja vrsta napake za iskanje, ker nič
v razliki ne kaže na tolmača.

**Rešitev ni ujemanje kopij.** Ena sama deklaracija: `.python-version`, ki jo bere `actions/setup-python`
prek `python-version-file:` in pyenv neposredno. Neujemanje se ne zazna, je nemogoče. LibrePT je to
pisal za trinajst `python-version:` v delovnih tokovih in pripadajoč preizkus, da se ujemajo, je bil
kontrola, katere delo je držati kopije vštric, torej oblika manjkajočega enega vira resnice.

Kar kontrola še preverja, je ožje in pošteno:

  1. **Ta računalnik teče na deklarirani različici.** Prava kontrola, ki je strukturno ni mogoče
     rešiti: računalnik razvijalca ni repozitorij.
  2. **Noben delovni tok ne pripne različice dobesedno** (`python-version: 3.11`) — jamstvo proti
     vrnitvi kopij, ne odkritje.

Samo manjša različica (3.11), ne popravki: te razlikujejo slike strojev in razvijalci upravičeno.

Zagon: `python -m agent_tools.python_version`
"""

import re
import sys
from pathlib import Path

from agent_tools._tree import ROOT

VERSION_FILE = ".python-version"
WORKFLOW_GLOB = ".github/**/*.y*ml"
LITERAL_PIN = re.compile(r"^\s*python-version:\s*['\"]?([0-9]+\.[0-9]+)", re.M)


def minor(version):
    return ".".join(str(version).strip().split(".")[:2])


def running_python():
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def declared_version(root):
    """Edina deklaracija ali "", če datoteke ni — to je že težava, ki jo je treba javiti."""
    try:
        return (Path(root) / VERSION_FILE).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def version_problems(root=None, running=None):
    """Težave kot stavki; prazno pomeni eno deklaracijo in ta računalnik na njej."""
    root = Path(root if root is not None else ROOT)
    declared = declared_version(root)
    local = minor(running if running is not None else running_python())
    problems = []
    if not declared:
        problems.append(
            f"{VERSION_FILE} manjka: je edina deklaracija, ki jo vsak delovni tok bere prek `python-version-file:`"
        )
    elif minor(declared) != local:
        problems.append(
            f"{VERSION_FILE} deklarira Python {declared}, ta računalnik ima {local}: "
            "ujemi ga lokalno ali spremeni deklaracijo, CI ji sledi"
        )
    for path in sorted(root.glob(WORKFLOW_GLOB)):
        for pinned in sorted(
            set(LITERAL_PIN.findall(path.read_text(encoding="utf-8")))
        ):
            problems.append(
                f"{path.relative_to(root).as_posix()} pripne Python {pinned} dobesedno: "
                f"uporabi `python-version-file: {VERSION_FILE}`, da je ena deklaracija, ne kopija"
            )
    return problems


def main(root=None):
    problems = version_problems(root)
    if problems:
        print(f"  ✗ Različica Pythona: {len(problems)} težav\n")
        for problem in problems:
            print(f"    {problem}")
        print(
            "\n    Ena deklaracija in ta računalnik na njej: zelen lokalni prehod, ki je tekel na drugem jeziku, ni dokaz za objavo."
        )
        return 1
    print(
        f"  ✓ Različica Pythona: ena deklaracija ({declared_version(root if root is not None else ROOT)}), ta računalnik jo izvaja."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
