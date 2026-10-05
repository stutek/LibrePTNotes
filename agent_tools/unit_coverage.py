"""`python -m agent_tools.unit_coverage` — čista logika, ki je izgubila enotne teste.

`src/domain/` in `src/data/` držita pravila, na katerih stoji vse ostalo: vrstni red zapisov, datum,
barvanje markdowna, shrambo, šifrirano kopijo. Njihovi testi (`tests/unit_js/`) tečejo v sekundi in
poimenujejo funkcijo, ki je padla. Nič ne opazi, ko se funkcija doda brez testa ali test izbriše;
LibrePT je to izmeril šele naknadno (dve funkciji brez testa, ena brez klicatelja).

**Kaj meri.** Požene enotne teste pod Nodovo lastno pokritostjo (`--experimental-test-coverage`,
brez paketa) in prebere delež vrstic, ki jih je modul izvedel. Isto drevo da isto število, zato
prag drži natančno. Pokritost v brskalniku se NE meri: niha s časom in ne vidi service workerja.

**Kaj zahteva.** Vsak modul v obsegu doseže `FLOOR` (90 %; izmerjeno ob pisanju: najslabši
čisti modul `backupFile.js` 95,7 %, ostali 100 %, torej je rezerva ~5 točk) z dvema zapisanima
izjemama:
  * `TESTED_IN_THE_BROWSER`: modul, katerega delo je brskalniški API (IndexedDB). Enotni test ga ne
    more držati; navedeni test v brskalniku ga drži in mora obstajati.
  * `HELD`: modul pod pragom, držan tam, kjer je; številka gre lahko samo gor, preverjanje pa pade,
    ko naraste za `RAISE_BY` brez vpisa, da izboljšava ne zrahlja držanja. Prazno je cilj.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from agent_tools._tree import ROOT

SCOPE = ("src/domain/", "src/data/")
TEST_GLOB = "tests/unit_js/**/*.test.mjs"
FLOOR = 90
HELD = {}
RAISE_BY = 5

# modul → test, ki ga drži (mora obstajati)
TESTED_IN_THE_BROWSER = {
    "src/data/idbBackend.js": "tests/e2e/test_flow.py",
}


def parse_lcov(text, root=ROOT):
    """{repo-relativna pot: odstotek izvedenih vrstic} iz poročila lcov."""
    found, path, lines, hit = {}, None, 0, 0
    for line in text.splitlines():
        if line.startswith("SF:"):
            path = Path(line[3:])
            if path.is_absolute():
                path = path.relative_to(root)
            path = path.as_posix()
        elif line.startswith("LF:"):
            lines = int(line[3:])
        elif line.startswith("LH:"):
            hit = int(line[3:])
        elif line == "end_of_record" and path:
            found[path] = 100.0 * hit / lines if lines else 100.0
    return found


def measure(node_path, root=ROOT):
    """Pokritost vsakega modula, ki ga enotni testi naložijo; None, če testi sami padejo ali jih ni."""
    tests = sorted(str(p.relative_to(root)) for p in Path(root).glob(TEST_GLOB))
    if not tests:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        lcov = Path(tmp) / "unit.lcov"
        command = [node_path, "--test", "--experimental-test-coverage"]
        command += [f"--test-coverage-include={prefix}**" for prefix in SCOPE]
        command += [
            "--test-reporter=lcov",
            f"--test-reporter-destination={lcov}",
            *tests,
        ]
        run = subprocess.run(command, cwd=root, capture_output=True, text=True)
        if run.returncode != 0 or not lcov.exists():
            return None
        return parse_lcov(lcov.read_text(encoding="utf-8"), Path(root).resolve())


def modules_in_scope(root=ROOT):
    return sorted(
        p.relative_to(root).as_posix()
        for prefix in SCOPE
        for p in (Path(root) / prefix).rglob("*.js")
    )


def breaches(
    modules,
    coverage,
    held=HELD,
    browser=TESTED_IN_THE_BROWSER,
    test_exists=None,
    root=ROOT,
):
    """Vsako pravilo, ki ga drevo krši, kot stavek."""
    if test_exists is None:
        test_exists = lambda rel: (Path(root) / rel).is_file()  # noqa: E731
    found = [
        f"{listed} je navedena tu in je ni več: odstrani vpis"
        for listed in sorted((set(held) | set(browser)) - set(modules))
    ]
    for module in modules:
        if module in browser:
            if not test_exists(browser[module]):
                found.append(f"{module} navaja {browser[module]}, ki ne obstaja")
            continue
        percent = coverage.get(module, 0.0)
        floor = held.get(module, FLOOR)
        if percent < floor:
            what = (
                "ga ne požene noben enotni test"
                if module not in coverage
                else f"je pri {percent:.1f} %"
            )
            found.append(f"{module} {what}, pod pragom {floor} %")
        elif module in held and percent >= FLOOR:
            found.append(f"{module} je dosegel {percent:.1f} %: odstrani ga iz HELD")
        elif module in held and percent >= floor + RAISE_BY:
            found.append(
                f"{module} je zrasel na {percent:.1f} %: nastavi HELD na {int(percent)}"
            )
    return found


def main(node_path=None):
    node_path = node_path or shutil.which("node")
    if not node_path:
        print("  (preskočeno: ni Nodovega izvajalnega okolja; CI ga ima vedno)")
        return 0
    coverage = measure(node_path)
    if coverage is None:
        print(
            f"  ✗ Enotni testi ({TEST_GLOB}) so padli ali jih ni, zato ni bilo kaj meriti."
        )
        return 1
    found = breaches(modules_in_scope(), coverage)
    for sentence in found:
        print(f"  ✗ {sentence}")
    if found:
        print(
            f"\n  Čista logika v {' in '.join(SCOPE)} je v tests/unit_js/ pokrita z {FLOOR} % vrstic.\n"
            "  Napiši test; za modul, katerega delo je brskalniški API, navedi test v TESTED_IN_THE_BROWSER."
        )
        return 1
    print(f"  ✓ Vsak modul čiste logike je na pragu {FLOOR} % ali nad njim.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
