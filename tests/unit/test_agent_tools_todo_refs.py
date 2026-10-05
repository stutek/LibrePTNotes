"""todo_refs: nobena datoteka razen TODO.md ne kaže na njegove razdelke."""

from agent_tools import todo_refs


def files_in(tmp_path, files):
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return [(rel, n) for rel, n, _line in todo_refs.find_all(tmp_path)]


def test_code_comment_pointing_at_a_todo_section_is_reported(tmp_path):
    found = files_in(tmp_path, {"src/a.js": "// uvod\n// glej TODO.md §2 za razlog\n"})
    assert found == [("src/a.js", 2)]


def test_link_to_a_todo_anchor_and_old_section_form_are_reported(tmp_path):
    found = files_in(
        tmp_path,
        {"README.md": "[x](TODO.md#odprto)\n", "src/b.js": "// TODO section 3 pravi\n"},
    )
    assert sorted(found) == [("README.md", 1), ("src/b.js", 1)]


def test_bare_section_sign_in_code_is_reported_but_named_document_is_not(tmp_path):
    found = files_in(
        tmp_path,
        {"src/c.js": "// glej §4\n// glej RFC 6350 §3.2\n// DATA_MODEL §1\n"},
    )
    assert found == [("src/c.js", 1)]


def test_markdown_bare_section_passes_only_when_the_document_has_it(tmp_path):
    own = "# Dok\n\n## 2. Svoj\n\nGlej §2.\n"
    away = "# Dok\n\n## 2. Svoj\n\nGlej §9.\n"
    assert files_in(tmp_path / "a", {"docs/x.md": own}) == []
    assert files_in(tmp_path / "b", {"docs/x.md": away}) == [("docs/x.md", 5)]


def test_todo_itself_and_naming_the_file_without_a_section_are_fine(tmp_path):
    found = files_in(
        tmp_path,
        {
            "TODO.md": "# T\n\nGlej TODO.md §3 in §1.\n",
            "src/d.js": "// odprto delo je v TODO.md\n",
            "docs/e.md": "Primer: `TODO.md §2` v kodi.\n",
        },
    )
    assert found == []


def test_main_exit_codes(tmp_path):
    (tmp_path / "ok").mkdir()
    (tmp_path / "ok" / "a.js").write_text("// nič\n", encoding="utf-8")
    (tmp_path / "bad").mkdir()
    (tmp_path / "bad" / "a.js").write_text("// TODO §1\n", encoding="utf-8")
    assert todo_refs.main(tmp_path / "ok") == 0
    assert todo_refs.main(tmp_path / "bad") == 1
