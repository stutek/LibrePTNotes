"""inline_styles: videz samo v CSS, edina izjema je --plan-pull v kopiji kretnje."""

from agent_tools import inline_styles


def found(tmp_path, files):
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return [(rel, n) for rel, n, _line in inline_styles.find_all(tmp_path)]


def test_assignment_to_style_is_reported_with_its_line(tmp_path):
    js = "const a = 1;\nel.style.gap = '4px';\nel.style['color'] = red;\nel.style.cssText = 'x';\n"
    assert found(tmp_path, {"src/ui/a.js": js}) == [
        ("src/ui/a.js", 2),
        ("src/ui/a.js", 3),
        ("src/ui/a.js", 4),
    ]


def test_comparing_style_and_reading_it_is_not_writing_it(tmp_path):
    js = "if (el.style.gap === '4px') {}\nconst g = el.style.gap;\n"
    assert found(tmp_path, {"src/ui/a.js": js}) == []


def test_style_attribute_in_html_or_template_is_reported(tmp_path):
    files = {
        "src/index.html": '<div style="color: red"></div>\n<div style=""></div>\n',
        "src/ui/b.js": 'const h = `<p style="margin:0">x</p>`;\n',
    }
    assert sorted(found(tmp_path, files)) == [("src/index.html", 1), ("src/ui/b.js", 1)]


def test_plan_pull_is_allowed_only_in_the_gesture_copy(tmp_path):
    call = 'blanket.style.setProperty("--plan-pull", `${px}px`);\n'
    assert found(tmp_path / "a", {"src/gesture/planPeek.js": call}) == []
    assert found(tmp_path / "b", {"src/ui/a.js": call}) == [("src/ui/a.js", 1)]


def test_any_other_property_is_reported_even_a_custom_one_in_the_copy(tmp_path):
    other = 'blanket.style.setProperty("--peek", "1");\nblanket.style.setProperty("gap", "1");\n'
    assert found(tmp_path, {"src/gesture/planPeek.js": other}) == [
        ("src/gesture/planPeek.js", 1),
        ("src/gesture/planPeek.js", 2),
    ]


def test_set_attribute_style_is_reported(tmp_path):
    assert found(tmp_path, {"src/ui/a.js": 'el.setAttribute("style", "x");\n'}) == [
        ("src/ui/a.js", 1)
    ]


def test_generated_documents_are_not_scanned(tmp_path):
    assert (
        found(tmp_path, {"src/privacy.html": '<td style="text-align:left">x</td>\n'})
        == []
    )


def test_main_exit_codes(tmp_path):
    (tmp_path / "ok" / "src").mkdir(parents=True)
    (tmp_path / "ok" / "src" / "a.js").write_text(
        "el.className = 'x';\n", encoding="utf-8"
    )
    (tmp_path / "bad" / "src").mkdir(parents=True)
    (tmp_path / "bad" / "src" / "a.js").write_text(
        "el.style.top = 0;\n", encoding="utf-8"
    )
    assert inline_styles.main(tmp_path / "ok") == 0
    assert inline_styles.main(tmp_path / "bad") == 1
