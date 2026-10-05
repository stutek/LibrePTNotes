"""unit_coverage: prag deleža vrstic na čisti logiki, izjema za brskalniške module, branje lcov."""

import shutil

import pytest

from agent_tools import unit_coverage

MODULES = ["src/domain/a.js", "src/data/b.js"]


def test_lcov_is_read_as_percent_of_lines_run(tmp_path):
    lcov = "SF:src/domain/a.js\nLF:10\nLH:9\nend_of_record\nSF:src/data/b.js\nLF:0\nLH:0\nend_of_record\n"
    assert unit_coverage.parse_lcov(lcov, tmp_path) == {
        "src/domain/a.js": 90.0,
        "src/data/b.js": 100.0,
    }


def test_absolute_paths_in_lcov_become_repo_relative(tmp_path):
    lcov = f"SF:{tmp_path}/src/domain/a.js\nLF:4\nLH:2\nend_of_record\n"
    assert unit_coverage.parse_lcov(lcov, tmp_path) == {"src/domain/a.js": 50.0}


def test_modules_at_or_above_the_floor_pass():
    coverage = {"src/domain/a.js": 100.0, "src/data/b.js": float(unit_coverage.FLOOR)}
    assert unit_coverage.breaches(MODULES, coverage, held={}, browser={}) == []


def test_module_below_floor_and_module_no_test_loads_are_reported():
    coverage = {"src/domain/a.js": 50.0}
    found = unit_coverage.breaches(MODULES, coverage, held={}, browser={})
    assert any("a.js" in s and "50.0" in s for s in found)
    assert any("b.js" in s and "noben enotni test" in s for s in found)


def test_browser_module_needs_its_named_test_to_exist():
    browser = {"src/data/b.js": "tests/medium/test_b.py"}
    coverage = {"src/domain/a.js": 100.0}
    present = unit_coverage.breaches(
        MODULES, coverage, held={}, browser=browser, test_exists=lambda rel: True
    )
    absent = unit_coverage.breaches(
        MODULES, coverage, held={}, browser=browser, test_exists=lambda rel: False
    )
    assert present == []
    assert any("test_b.py" in s and "ne obstaja" in s for s in absent)


def test_entry_for_a_module_that_no_longer_exists_is_reported():
    found = unit_coverage.breaches(
        ["src/domain/a.js"],
        {"src/domain/a.js": 100.0},
        held={},
        browser={"src/data/gone.js": "t.py"},
        test_exists=lambda rel: True,
    )
    assert any("gone.js" in s and "ni več" in s for s in found)


def test_held_module_may_only_rise_and_entry_must_follow():
    modules, held = ["src/domain/a.js"], {"src/domain/a.js": 60}
    assert (
        unit_coverage.breaches(
            modules, {"src/domain/a.js": 62.0}, held=held, browser={}
        )
        == []
    )
    assert any(
        "pod pragom 60" in s
        for s in unit_coverage.breaches(
            modules, {"src/domain/a.js": 55.0}, held=held, browser={}
        )
    )
    assert any(
        "HELD na 70" in s
        for s in unit_coverage.breaches(
            modules, {"src/domain/a.js": 70.0}, held=held, browser={}
        )
    )
    assert any(
        "odstrani ga iz HELD" in s
        for s in unit_coverage.breaches(
            modules, {"src/domain/a.js": 95.0}, held=held, browser={}
        )
    )


@pytest.mark.skipif(
    shutil.which("node") is None, reason="ni Nodovega izvajalnega okolja"
)
def test_node_measures_a_covered_and_an_uncovered_module(tmp_path):
    (tmp_path / "src" / "domain").mkdir(parents=True)
    (tmp_path / "src" / "domain" / "m.js").write_text(
        "export function used() { return 1; }\nexport function unused() {\n  return 2;\n}\n",
        encoding="utf-8",
    )
    (tmp_path / "tests" / "unit_js" / "domain").mkdir(parents=True)
    (tmp_path / "tests" / "unit_js" / "domain" / "m.test.mjs").write_text(
        'import { test } from "node:test";\nimport assert from "node:assert/strict";\n'
        'import { used } from "../../../src/domain/m.js";\ntest("used", () => assert.equal(used(), 1));\n',
        encoding="utf-8",
    )
    coverage = unit_coverage.measure(shutil.which("node"), tmp_path)
    assert 0 < coverage["src/domain/m.js"] < 100


def test_measure_reports_missing_suite_as_none(tmp_path):
    assert unit_coverage.measure("node", tmp_path) is None
