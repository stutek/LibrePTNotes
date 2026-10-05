"""css_tokens: neopredeljena lastnost in paritetni del svetle in temne teme."""

from agent_tools import css_tokens

LIGHT_DARK = """
:root { --bg: #fff; --fg: #000; --safe: env(safe-area-inset-bottom, 0px); }
@media (prefers-color-scheme: dark) { :root { --bg: #111; --fg: #eee; } }
"""


def project(tmp_path, files):
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def test_defined_property_is_fine_and_undefined_one_is_reported(tmp_path):
    css = LIGHT_DARK + "a { color: var(--fg); background: var(--nope, red); }\n"
    undefined, gaps = css_tokens.find_all(project(tmp_path, {"src/app.css": css}))
    assert [(where, name) for where, name in undefined] == [("src/app.css:4", "--nope")]
    assert gaps == []


def test_property_written_by_javascript_counts_as_defined(tmp_path):
    root = project(
        tmp_path,
        {
            "src/app.css": ":root { --a: #fff; }\n@media (prefers-color-scheme: dark) { :root { --a: #000; } }\n"
            "b { transform: translateX(var(--pull, 0px)); }\n",
            "src/g.js": 'el.style.setProperty("--pull", "4px");\n',
        },
    )
    assert css_tokens.find_all(root) == ([], [])


def test_declared_fallback_hook_of_the_copy_passes_only_there(tmp_path):
    use = "x { transform: translateY(var(--peek-align, 0px)); }\n"
    in_copy = project(tmp_path / "a", {"src/gesture/planPeek.css": use})
    elsewhere = project(tmp_path / "b", {"src/app.css": use})
    assert css_tokens.find_all(in_copy)[0] == []
    assert [name for _where, name in css_tokens.find_all(elsewhere)[0]] == [
        "--peek-align"
    ]


def test_colour_only_in_dark_theme_is_a_parity_gap(tmp_path):
    css = ":root { --a: #fff; }\n@media (prefers-color-scheme: dark) { :root { --a: #000; --b: #123; } }\n"
    _undefined, gaps = css_tokens.find_all(project(tmp_path, {"src/app.css": css}))
    assert [message.split()[0] for _rel, message in gaps] == ["--b"]


def test_colour_only_in_light_theme_is_a_gap_but_non_colour_is_not(tmp_path):
    css = (
        ":root { --a: #fff; --c: #007acc; --pad: 8px; --safe: env(safe-area-inset-bottom, 0px); }\n"
        "@media (prefers-color-scheme: dark) { :root { --a: #000; } }\n"
    )
    _undefined, gaps = css_tokens.find_all(project(tmp_path, {"src/app.css": css}))
    assert [message.split()[0] for _rel, message in gaps] == ["--c"]


def test_reduced_motion_media_is_not_a_theme(tmp_path):
    css = ":root { --a: #fff; }\n@media (prefers-reduced-motion: reduce) { :root { --m: #000; } }\n"
    assert css_tokens.find_all(project(tmp_path, {"src/app.css": css}))[1] == []


def test_main_exit_codes(tmp_path):
    ok = project(
        tmp_path / "ok", {"src/app.css": LIGHT_DARK + "a { color: var(--fg); }\n"}
    )
    bad = project(tmp_path / "bad", {"src/app.css": "a { color: var(--zz); }\n"})
    assert css_tokens.main(ok) == 0
    assert css_tokens.main(bad) == 1
