"""Seznam datotek repozitorija, skupen kontrolam (ni samostojno orodje).

Zakaj: nova datoteka, ki je še ni v gitu, je prav tista, ki jo bo naslednji commit prinesel, zato jo
mora kontrola videti pred commitom. `git ls-files --cached --others --exclude-standard` jo vidi, golo
`git ls-files` ne. Brez gita (testna drevesa v tmp_path) se drevo sprehodi samo.
"""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIPPED_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".pytest_cache"}


def repo_files(root=None):
    """Repo-relativne poti (POSIX), ki obstajajo na disku, urejene."""
    root = Path(root) if root is not None else ROOT
    names = None
    if (root / ".git").exists():
        run = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            capture_output=True,
            text=True,
        )
        if run.returncode == 0:
            names = [line for line in run.stdout.splitlines() if line]
    if names is None:
        names = [
            p.relative_to(root).as_posix()
            for p in root.rglob("*")
            if p.is_file() and not SKIPPED_DIRS & set(p.relative_to(root).parts)
        ]
    return sorted(n for n in set(names) if (root / n).is_file())


def read(root, rel):
    return (Path(root) / rel).read_text(encoding="utf-8")
