"""complexity: McCabe po funkcijah s pravo slovnico, prag 15."""

import pytest

from agent_tools import complexity


def scores(source):
    return {
        name: value for _label, _line, name, value in complexity.analyze_source(source)
    }


def test_straight_line_function_is_one():
    assert scores("function f() { return 1; }") == {"f": 1}


def test_branches_loops_catch_and_ternary_each_add_one():
    source = """
    function f(a, b) {
      if (a) { return 1; } else if (b) { return 2; }
      for (const x of a) {}
      while (b) { break; }
      try { g(); } catch (e) {}
      return a ? 1 : 2;
    }"""
    assert scores(source)["f"] == 1 + 2 + 1 + 1 + 1 + 1


def test_logical_operators_and_optional_chaining_are_counted_correctly():
    chain = "function f(a, b, c) { return a && b && c; }"
    nullish = "function g(a) { return a?.b ?? a?.c ?? 0; }"
    assert scores(chain)["f"] == 3
    assert scores(nullish)["g"] == 3


def test_switch_counts_cases_but_not_default():
    source = "function f(x) { switch (x) { case 1: return 1; case 2: return 2; default: return 0; } }"
    assert scores(source)["f"] == 3


def test_nested_function_does_not_inherit_the_outer_count():
    source = "function outer(a) { const inner = () => { if (a) { return 1; } return 2; }; return inner; }"
    assert scores(source) == {"outer": 1, "inner": 2}


def test_over_limit_keeps_only_functions_above_the_ceiling():
    branches = "".join(
        f"if (a{i}) {{ x++; }}\n" for i in range(complexity.MAX_COMPLEXITY)
    )
    heavy = f"function heavy(a) {{ {branches} }}"
    light = "function light(a) { if (a) { return 1; } return 2; }"
    over = complexity.over_limit(complexity.analyze_source(heavy + light))
    assert [name for _label, _line, name, _value in over] == ["heavy"]


@pytest.mark.parametrize("extra,code", [(0, 0), (2, 1)])
def test_main_gates_a_tree_on_the_ceiling(tmp_path, extra, code):
    branches = "".join(
        f"if (a{i}) {{ x++; }}\n" for i in range(complexity.MAX_COMPLEXITY - 1 + extra)
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.js").write_text(
        f"export function f(a) {{ {branches} }}\n", encoding="utf-8"
    )
    assert complexity.main(tmp_path) == code
