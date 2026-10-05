"""test_assertions: oblike, vezane na mehaniko, in zapisani razlog, ki jih pobriše.

Datoteka vsebuje namenske kršitve v nizih; kontrola jo izpusti po imenu (izpuščanje detektorja ni
izjema od pravila, ampak pogoj, da ga je sploh mogoče preizkusiti).
"""

from pathlib import Path

from agent_tools import test_assertions as ta


def scan(tmp_path, name, text):
    root = tmp_path / name
    (root / "tests").mkdir(parents=True)
    (root / "tests" / name).write_text(text, encoding="utf-8")
    return [
        (Path(path).name, line) for path, line, _msg in ta.collect_findings(root=root)
    ]


def test_trivial_and_self_equal_assertions_are_reported(tmp_path):
    py = "def test_a():\n    assert True\n\n\ndef test_b():\n    x = 1\n    assert x == 1\n"
    mjs = 'test("a", () => {\n  assert.ok(true);\n  assert.equal(1, 1);\n});\n'
    assert scan(tmp_path, "test_t.py", py) == [("test_t.py", 2)]
    assert scan(tmp_path, "a.test.mjs", mjs) == [("a.test.mjs", 2), ("a.test.mjs", 3)]


def test_test_without_any_assertion_is_reported_in_both_languages(tmp_path):
    py = "def test_a():\n    run()\n\n\ndef test_b():\n    assert run() == 1\n\n\ndef test_c(page):\n    expect(page).to_have_title('x')\n"
    mjs = 'test("bez", () => {\n  run();\n});\n\ntest("z", () => {\n  assert.equal(run(), 1);\n});\n'
    assert scan(tmp_path, "test_t.py", py) == [("test_t.py", 1)]
    assert scan(tmp_path, "b.test.mjs", mjs) == [("b.test.mjs", 1)]


def test_helper_that_waits_or_checks_counts_as_an_assertion(tmp_path):
    py = "def test_a(page):\n    wait_for_saved(page, 'x')\n\n\ndef test_b(page):\n    check_state(page)\n\n\ndef test_c(page):\n    eventually(page, lambda: True)\n"
    assert scan(tmp_path, "test_t.py", py) == []


def test_stub_call_counting_is_reported(tmp_path):
    py = "def test_a(m):\n    run(m)\n    m.assert_called_once()\n    assert m.call_count == 1\n"
    mjs = 'test("a", () => {\n  const f = mock.fn();\n  assert.equal(f.mock.calls.length, 1);\n});\n'
    assert [line for _n, line in scan(tmp_path, "test_t.py", py)] == [3, 4]
    assert [line for _n, line in scan(tmp_path, "c.test.mjs", mjs)] == [3]


def test_reference_identity_is_reported_but_constants_and_literals_are_not(tmp_path):
    mjs = 'test("a", () => {\n  assert.equal(state, before);\n  assert.equal(RESULT, EXPECTED);\n  assert.equal(x, null);\n  assert.equal(state.a, 1);\n});\n'
    py = "def test_a():\n    a = make()\n    b = make()\n    assert a is b\n    assert a is not None\n"
    assert scan(tmp_path, "d.test.mjs", mjs) == [("d.test.mjs", 2)]
    assert scan(tmp_path, "test_t.py", py) == [("test_t.py", 4)]


def test_pattern_assertions_on_source_text_are_reported_but_not_on_parsed_data(
    tmp_path,
):
    mjs = (
        'const SRC = new URL("../src/", import.meta.url).pathname;\n'
        'const sw = readFileSync(join(SRC, "sw.js"), "utf8");\n'
        'test("a", () => {\n  assert.match(sw, /CACHE/);\n});\n'
        'test("b", () => {\n  const m = JSON.parse(readFileSync(join(SRC, "m.json"), "utf8"));\n  assert.equal(m.name, "x");\n});\n'
    )
    assert scan(tmp_path, "e.test.mjs", mjs) == [("e.test.mjs", 4)]


def test_reading_other_files_and_comparing_bytes_is_not_source_text(tmp_path):
    py = (
        "def test_a(tmp_path):\n"
        "    out = (tmp_path / 'dist' / 'a.txt').read_text()\n"
        "    assert out == 'x'\n"
        "    assert (tmp_path / 'src' / 'a.js').read_bytes() == (tmp_path / 'dist' / 'a.js').read_bytes()\n"
    )
    assert scan(tmp_path, "test_t.py", py) == []


def test_exact_multi_class_assertion_is_reported_single_class_is_not(tmp_path):
    py = "def test_a(page):\n    expect(page).to_have_class('btn primary big')\n    expect(page).to_have_class('btn')\n"
    assert scan(tmp_path, "test_t.py", py) == [("test_t.py", 2)]


def test_counter_that_is_never_read_is_reported(tmp_path):
    js = "window.__ticks = 0;\nwindow.__ticks++;\nwindow.__seen = 0;\nwindow.__seen++;\ncheck(window.__seen);\n"
    found = scan(tmp_path, "f.test.mjs", js)
    assert [line for _n, line in found] == [1]


def test_named_reason_clears_a_finding_on_the_line_or_just_above(tmp_path):
    py = (
        "def test_a(m):\n"
        "    run(m)\n"
        "    # avoided side effect: nothing may be sent\n"
        "    assert m.call_count == 0\n"
        "    assert m.call_count == 1  # persisted format of the log\n"
        "    assert m.call_count == 2\n"
    )
    assert scan(tmp_path, "test_t.py", py) == [("test_t.py", 6)]


def test_detector_test_file_and_conftest_are_skipped(tmp_path):
    assert (
        scan(
            tmp_path,
            "test_agent_tools_test_assertions.py",
            "def test_a():\n    assert True\n",
        )
        == []
    )
    assert scan(tmp_path, "conftest.py", "def test_x():\n    pass\n") == []


def test_main_exit_codes(tmp_path):
    (tmp_path / "ok" / "tests").mkdir(parents=True)
    (tmp_path / "ok" / "tests" / "test_t.py").write_text(
        "def test_a():\n    assert 1 + 1 == 2\n", encoding="utf-8"
    )
    (tmp_path / "bad" / "tests").mkdir(parents=True)
    (tmp_path / "bad" / "tests" / "test_t.py").write_text(
        "def test_a():\n    assert True\n", encoding="utf-8"
    )
    assert ta.main(tmp_path / "ok") == 0
    assert ta.main(tmp_path / "bad") == 1
