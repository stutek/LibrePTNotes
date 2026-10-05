"""`python -m agent_tools.test_assertions` — testi držijo vedenje, ne mehanike.

Zakaj: test mora trditi vedenje, na katero se klicatelj zanaša, ne mehanike, ki ga proizvede. Test,
ki kodira, KAKO koda dela, pade ob vsakem preoblikovanju, ki nič ne spremeni, in zato kaznuje
čiščenje; hkrati ostane zelen, ko je vedenje pokvarjeno, če mehanika preživi. V pregledu ni vidno
nič od tega: trditev je videti natančna, in prav zato prepričljiva.

Kontrola ne bere vsega, ker to ne bi zdržalo (z naslednjim testom bi zastarala); zazna samo oblike,
ki so strojno prepoznavne in vse že videne v LibrePT. Velja za `node:test` (`.test.mjs`, `.mjs`,
`.js`) in `pytest` (`.py`) pod `tests/`:

  1. **Prazna trditev** — `assert True`, `assert.ok(true)`, `assert.equal(x, x)`: nič ne preverja.
  2. **Test brez trditve** — `test(…)` / `def test_…` brez `assert`, `assert.rejects`, `pytest.raises`
     ali klica pomočnika `assert…`/`check…`/`verify…`/`expect…`: zelen, ker nič ne trdi.
  3. **Števci klicev na lažnem objektu** — `mock.calls`, `callCount`, `call_count`,
     `assert_called…`: trdi, kolikokrat se je nekaj poklicalo, ne kaj se je zgodilo.
  4. **Identiteta namesto vrednosti** — `assert.equal(a, b)` med dvema spremenljivkama ali
     `assert a is b`: »isti objekt se je vrnil« je izvedbena odločitev; obljuba je `deepEqual`.
  5. **Primerjava z izvornim besedilom** — test prebere datoteko iz `src/` kot besedilo in trdi, kaj
     vsebuje (`includes`, `match`, `in`): preverja zapis kode, ne vedenje.
  6. **Točna večrazredna trditev** — `to_have_class("a b c")` (Playwright): zlomi se ob vsakem
     preoblikovanju stila.
  7. **Mrtev števec** — `window.__x = 0` s `++`, ki ga nihče ne prebere.

**Vsaka najdba se pobriše samo z zapisanim razlogom**, v komentarju na vrstici ali tik nad njo, ki
imenuje enega od treh upravičenih primerov: zapisani format, ki preživi kodo (`persisted format`),
pogodba datoteke (`is the contract`) ali preprečen stranski učinek (`avoided side effect`).
To ni seznam dolga: izjema pravila zahteva razlog, zato sta izhod in pravilo ista zahteva.
Česa ne vidi: ime po funkciji namesto po obljubi, preveč lažnih objektov, ki zrcalijo izvedbo, in
trditev o resničnem, a nepomembnem vedenju. Za to potrebuješ bralca.
"""

import ast
import re
import sys
from pathlib import Path

from agent_tools._tree import ROOT

JUSTIFICATION = re.compile(
    r"persisted[- ]format|behaviour carve-out|is the contract|avoided side effect", re.I
)

TRIVIAL = re.compile(
    r"\bassert\s+(?:True|1)\s*(?:,|$|#)|assert(?:\.ok)?\(\s*(?:true|1)\s*[,)]"
)
SELF_EQUAL = re.compile(
    r"assert\.(?:equal|strictEqual|deepEqual)\(\s*([\w$.]+|[\"'`][^\"'`]*[\"'`]|\d+)\s*,\s*\1\s*[,)]"
)
EXACT_CLASS = re.compile(r"""to_have_class\(\s*["']([^"']*\s+[^"']*)["']""")
CALL_COUNT = re.compile(
    r"""\.mock\.calls|\.mock\.callCount|\b(?:callCount|call_count)\b|\bassert_(?:called|has_calls|not_called)\w*"""
    r"""|(?:assert\w*|expect)\s*\(?[^)\n]*\b\w+\.(?:created|updated|deleted|calls)\b"""
)
IDENTITY = re.compile(
    r"assert\.(?:equal|strictEqual)\(\s*([A-Za-z_$][\w$]*)\s*,\s*([A-Za-z_$][\w$]*)\s*\)"
)
IDENTITY_IS = re.compile(r"^\s*assert\s+\w+\s+is\s+(?!None\b|not\b|True\b|False\b)\w+")
NAMED_CONSTANT = re.compile(r"^[A-Z][A-Z0-9_]*$")
IDENTITY_OK = {"true", "false", "null", "undefined", "NaN"}
READS_FILE = re.compile(r"\b(?:readFileSync|readFile|read_text|read_bytes)\(")
# Datoteka omenja src/: pot z `src/`, `"src"` ali konstanta SRC (preberi jo, ko se zdi primerno).
SRC_PATH = re.compile(r"""\bsrc/|["'`]src["'`]|\bSRC\b|/src\b""")
COUNTER_DECL = re.compile(
    r"(window\.)?(__\w+)\s*=\s*(?:0|\(window\.__\w+\s*\|\|\s*0\))"
)
COUNTER_BOOKKEEPING = re.compile(r"=\s*(?:0|\(window\.__\w+\s*\|\|\s*0\))|\+\+|\+=")
JS_TEST_START = re.compile(r"^\s*(?:test|it)\s*(?:\.\w+)?\(\s*([\"'`])(.+?)\1")
HAS_ASSERTION = re.compile(
    r"\bassert\w*\b|\bt\.assert|\bexpect\w*\(|\bcheck\w*\(|\bverify\w*\(|\.rejects\(|\.throws\("
)
SELF_TEST_FILE = "test_agent_tools_test_assertions.py"


def justified(lines, index):
    """Vrstica ali komentar tik nad njo imenuje upravičeni primer."""
    if JUSTIFICATION.search(lines[index]):
        return True
    for above in range(index - 1, max(-1, index - 4), -1):
        stripped = lines[above].strip()
        if not stripped.startswith(("#", "//", "*")):
            break
        if JUSTIFICATION.search(stripped):
            return True
    return False


def line_findings(lines):
    """[(vrstica od 1, sporočilo)] za enovrstične oblike."""
    found = []
    for i, line in enumerate(lines):
        if justified(lines, i):
            continue
        if TRIVIAL.search(line) or SELF_EQUAL.search(line):
            found.append((i + 1, "prazna trditev: nič ne preverja"))
        if EXACT_CLASS.search(line):
            found.append(
                (
                    i + 1,
                    "točen niz razredov: trdi, kar uporabnik vidi (to_be_visible / to_have_text)",
                )
            )
        if CALL_COUNT.search(line):
            found.append(
                (
                    i + 1,
                    "trdi število klicev lažnega objekta: trdi izid teh klicev ali ime preprečeni stranski učinek",
                )
            )
        identity = IDENTITY.search(line)
        if (
            identity
            and not (set(identity.groups()) & IDENTITY_OK)
            and not any(NAMED_CONSTANT.match(g) for g in identity.groups())
        ):
            found.append(
                (
                    i + 1,
                    f"assert.equal({identity.group(1)}, {identity.group(2)}) primerja reference: uporabi deepEqual",
                )
            )
        elif IDENTITY_IS.search(line):
            found.append(
                (
                    i + 1,
                    "`is` primerja identiteto objektov: obljuba je enakost vrednosti",
                )
            )
    return found


def source_text_findings(lines):
    """Besedilo datoteke iz src/, na katerem test išče vzorec: preverja zapis kode, ne vedenja.

    Sledi se spremenljivki, ki prejme prebrano datoteko, in vsaki, izpeljani iz nje; ugotovitev je
    trditev o besedilu (`assert.match(sw, …)`, `sw.includes(…)`, `"x" in sw`, `re.search(…, sw)`).
    Razčlenjen JSON ali primerjava bajtov ni besedilna trditev in se ne šteje.
    """
    tainted, found = set(), []
    for i, line in enumerate(lines):
        assignment = re.match(r"\s*(?:const|let|var)?\s*(\w+)\s*=(?!=)\s*(.*)", line)
        if assignment:
            name, value = assignment.groups()
            reads_source = READS_FILE.search(value) and SRC_PATH.search(value)
            parsed = re.search(r"JSON\.parse|json\.loads|\.read_bytes\(", value)
            if (reads_source and not parsed) or (
                tainted and any(re.search(rf"\b{t}\b", value) for t in tainted)
            ):
                tainted.add(name)
        if justified(lines, i):
            continue
        for name in tainted:
            n = re.escape(name)
            if re.search(
                rf"assert\.(?:match|doesNotMatch)\(\s*{n}\b|\b{n}\.(?:includes|match|test)\(|[\"'`]\s+in\s+{n}\b|re\.search\([^)]*\b{n}\b",
                line,
            ):
                found.append(
                    (
                        i + 1,
                        f"trdi besedilo datoteke iz src/ (`{name}`): preveri vedenje, ne zapis kode",
                    )
                )
                break
    return found


def dead_counter_findings(lines):
    found = []
    for i, line in enumerate(lines):
        match = COUNTER_DECL.search(line)
        if not match or justified(lines, i):
            continue
        name = match.group(2)
        if not [
            other
            for other in lines
            if name in other and not COUNTER_BOOKKEEPING.search(other)
        ]:
            found.append(
                (
                    i + 1,
                    f"`{name}` se vzdržuje in ga nihče ne prebere: izbriši ga ali trdi vedenje, ki naj bi ga dokazal",
                )
            )
    return found


def js_tests_without_assertion(lines):
    """`test("…", () => { … })` brez katerekoli trditve v telesu."""
    found = []
    for i, line in enumerate(lines):
        if not JS_TEST_START.match(line) or justified(lines, i):
            continue
        depth, body, started = 0, [], False
        for later in lines[i:]:
            body.append(later)
            depth += later.count("{") - later.count("}")
            started = started or "{" in later
            if started and depth <= 0:
                break
        if started and not HAS_ASSERTION.search("\n".join(body[1:])):
            found.append((i + 1, "test nima nobene trditve: zelen je, ker nič ne trdi"))
    return found


def _has_assertion(node):
    for child in ast.walk(node):
        if isinstance(child, ast.Assert):
            return True
        if isinstance(child, ast.Call):
            name = ast.unparse(child.func)
            if re.search(
                r"raises|warns|\bfail\b|\.assert|^assert|^check|^verify|^expect|^wait_for|^eventually|_assert|\bexpect\b",
                name,
            ):
                return True
    return False


def py_tests_without_assertion(text, lines):
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    return [
        (node.lineno, f"{node.name}: test nima nobene trditve")
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name.startswith("test_")
        and not _has_assertion(node)
        and not justified(lines, node.lineno - 1)
    ]


def file_findings(path, text):
    lines = text.splitlines()
    found = (
        line_findings(lines)
        + source_text_findings(lines)
        + dead_counter_findings(lines)
    )
    if path.suffix == ".py":
        found += py_tests_without_assertion(text, lines)
    else:
        found += js_tests_without_assertion(lines)
    return sorted(set(found))


def collect_findings(tests_dir=None, root=None):
    root = Path(root if root is not None else ROOT)
    tests_dir = Path(tests_dir) if tests_dir is not None else root / "tests"
    findings = []
    for path in sorted(tests_dir.rglob("*")):
        if (
            path.suffix not in {".py", ".mjs", ".js"}
            or not path.is_file()
            or path.name == SELF_TEST_FILE
        ):
            continue
        if "__pycache__" in path.parts or path.name == "conftest.py":
            continue
        shown = path.relative_to(root) if path.is_relative_to(root) else path
        findings += [
            (shown, n, message)
            for n, message in file_findings(path, path.read_text(encoding="utf-8"))
        ]
    return findings


def main(root=None):
    findings = collect_findings(root=root)
    if findings:
        print(
            f"\n  ✗ Trditve testov: {len(findings)} vezanih na mehaniko namesto na vedenje\n"
        )
        for path, line, message in findings:
            print(f"    {path}:{line}  {message}")
        print(
            "\n    Vprašaj pri vsaki: če bi notranjost prepisali in obljubo ohranili, bi vrstica še držala?\n"
            "    Premišljena izjema se pobriše z imenovanjem v komentarju: persisted format, is the contract\n"
            "    ali avoided side effect."
        )
        return 1
    print("  ✓ Trditve testov: vsaka preverjena trditev drži vedenje, ne mehanike.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
