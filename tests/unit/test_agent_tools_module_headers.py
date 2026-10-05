"""module_headers: samotrditev poti v prvi vrstici mora držati; proza in kopija iz LibrePT ne trdita nič."""

from agent_tools import module_headers


def src(tmp_path, files):
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def test_correct_self_path_passes(tmp_path):
    root = src(
        tmp_path,
        {"src/domain/notes.js": "// src/domain/notes.js — vrstni red\nexport {};\n"},
    )
    assert module_headers.wrong_headers(root) == []


def test_wrong_self_path_is_reported_with_both_paths(tmp_path):
    root = src(tmp_path, {"src/ui/tabs.js": "// src/views/tabs.js — zavihki\n"})
    assert module_headers.wrong_headers(root) == [
        ("src/ui/tabs.js", "src/views/tabs.js")
    ]


def test_prose_header_and_mentioning_another_module_make_no_claim(tmp_path):
    root = src(
        tmp_path,
        {
            "src/a.js": "// Vstopna točka aplikacije.\n",
            "src/b.js": "// Pomočnik za src/domain/notes.js, ki ga ne ponavlja\n",
            "src/c.js": "export const x = 1;\n",
        },
    )
    assert module_headers.wrong_headers(root) == []


def test_copy_from_librept_is_not_judged_by_its_second_line(tmp_path):
    copy = (
        "// Kopija iz LibrePT: src/modules/clipboard/planPeek.js, commit 403715f9.\n"
        "// src/modules/clipboard/planPeek.js — opis iz LibrePT\n"
    )
    root = src(tmp_path, {"src/gesture/planPeek.js": copy})
    assert module_headers.wrong_headers(root) == []


def test_only_the_first_line_counts(tmp_path):
    root = src(tmp_path, {"src/a.js": "// Opis.\n// src/other/a.js — druga vrstica\n"})
    assert module_headers.wrong_headers(root) == []


def test_main_exit_codes(tmp_path, capsys):
    ok = src(tmp_path / "ok", {"src/a.js": "// src/a.js — opis\n"})
    bad = src(tmp_path / "bad", {"src/a.js": "// src/b.js — opis\n"})
    assert module_headers.main(ok) == 0
    assert module_headers.main(bad) == 1
    assert "src/a.js:1" in capsys.readouterr().out
