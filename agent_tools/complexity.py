"""`python -m agent_tools.complexity` — ciklomatska zahtevnost funkcij v src/**/*.js.

Zakaj: aplikacija nima linterja zahtevnosti, ruff pa vidi samo Python. Funkcija, ki je tiho zrasla v
ducat vej, se v pregledu bere vrstico za vrstico brez težav; ujame jo samo štetje vseh odločitev
naenkrat, česar človek ne dela zanesljivo.

Razčlenjevanje s pravo slovnico (`tree_sitter_javascript`), ne z regexom: koda uporablja `?.` in
`??`, ki bi ju regex bodisi napačno štel bodisi se na njiju spotaknil.

McCabe na funkcijo: 1 + ena za vsako odločitveno točko: `if`/`else if`, zanke, `catch`, ternarni
operator, `case` v `switch` in vsak `&&` / `||` / `??` (`a && b && c` so tri poti, ne ena).
Gnezdene funkcije se ocenjujejo ločeno in ne podedujejo števila zunanje.

Prag je `MAX_COMPLEXITY` = 15, kot v LibrePT: nad njim je funkcija preveč za pregled ali test kot
celoto. Izjem in seznama dolga ni: vsaka funkcija nad pragom pade, razdeli jo. Kretnja
`src/gesture/planPeek.js` je prevzeta kopija, ki mora ostati nespremenjena, in jo prag brez izjeme
prepusti (najzahtevnejša funkcija, `pointermove`, je 14); če bi kopija kdaj narasla čez prag, je
pravi odgovor posodobitev kopije iz LibrePT ali izrecna odločitev lastnika, ne tihi seznam izjem.
"""

import sys
from pathlib import Path

import tree_sitter_javascript as tsjs
from tree_sitter import Language, Parser

from agent_tools._tree import ROOT

MAX_COMPLEXITY = 15

FUNCTION_NODES = {
    "function_declaration",
    "function_expression",
    "arrow_function",
    "method_definition",
    "generator_function_declaration",
    "generator_function",
}
DECISION_NODES = {
    "if_statement",
    "for_statement",
    "for_in_statement",
    "while_statement",
    "do_statement",
    "catch_clause",
    "ternary_expression",
    "switch_case",  # switch_default je svoj tip vozlišča in se ne šteje
}
LOGICAL = {"&&", "||", "??"}

_LANGUAGE = Language(tsjs.language())


def function_name(node):
    """Ime funkcije za poročilo (najboljši poskus; zahtevnosti ne vpliva)."""
    named = node.child_by_field_name("name")
    if named is not None:
        return named.text.decode("utf-8")
    parent = node.parent
    if parent is not None:
        field = {
            "variable_declarator": "name",
            "pair": "key",
            "assignment_expression": "left",
        }.get(parent.type)
        target = parent.child_by_field_name(field) if field else None
        if target is not None:
            return target.text.decode("utf-8")
    return "<anonimna>"


def _walk(node, stack, findings, label):
    is_function = node.type in FUNCTION_NODES
    if is_function:
        stack.append({"complexity": 1, "line": node.start_point[0] + 1})
    if stack:
        if node.type in DECISION_NODES:
            stack[-1]["complexity"] += 1
        elif node.type == "binary_expression":
            operator = node.child_by_field_name("operator")
            if operator is not None and operator.text.decode("utf-8") in LOGICAL:
                stack[-1]["complexity"] += 1
    for child in node.children:
        _walk(child, stack, findings, label)
    if is_function:
        done = stack.pop()
        findings.append((label, done["line"], function_name(node), done["complexity"]))


def analyze_source(source, label=""):
    """[(oznaka, vrstica, ime, zahtevnost)] za VSAKO funkcijo; filtriranje je stvar klicatelja."""
    data = source if isinstance(source, bytes) else source.encode("utf-8")
    findings = []
    _walk(Parser(_LANGUAGE).parse(data).root_node, [], findings, label)
    return findings


def over_limit(findings):
    """Podmnožica ugotovitev nad MAX_COMPLEXITY."""
    return [f for f in findings if f[3] > MAX_COMPLEXITY]


def find_all(root=None):
    root = Path(root if root is not None else ROOT)
    found, count = [], 0
    for path in sorted((root / "src").rglob("*.js")):
        rel = path.relative_to(root).as_posix()
        count += 1
        found += over_limit(analyze_source(path.read_bytes(), rel))
    return found, count


def main(root=None):
    found, count = find_all(root)
    if found:
        print(f"\n  ✗ Ciklomatska zahtevnost: {len(found)} funkcij nad mejo\n")
        for rel, line, name, value in found:
            print(f"    {rel}:{line}  {name}() — zahtevnost {value}")
        print(
            "\n    Razdeli funkcijo ali izvleči vejo; kaj se šteje, piše v agent_tools/complexity.py."
        )
        return 1
    print(
        f"  ✓ Ciklomatska zahtevnost: {count} datotek, vsaka funkcija ≤ {MAX_COMPLEXITY}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
