"""doclinks: frontmatter, kazalo, povezave in razdelki na umetnih drevesih v tmp_path."""

from agent_tools import doclinks

FRONT = '---\ntype: doc\ntitle: "T"\ndescription: "D"\ntags: [a]\n---\n\n'


def tree(tmp_path, files):
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def messages(root):
    findings, _count = doclinks.find_all(root)
    return [f"{rel}:{n} {message}" for rel, n, message in findings]


def healthy(extra=None):
    files = {
        "index.md": FRONT + "* [A](a.md)\n",
        "a.md": FRONT + "# A\n\n## 1. Prvi\n\nBesedilo.\n",
    }
    files.update(extra or {})
    return files


def test_healthy_tree_has_no_findings(tmp_path):
    assert messages(tree(tmp_path, healthy())) == []


def test_missing_frontmatter_key_is_reported(tmp_path):
    root = tree(tmp_path, healthy({"a.md": "---\ntype: doc\ntitle: T\n---\n# A\n"}))
    found = messages(root)
    assert any("a.md" in m and "description" in m for m in found)
    assert any("a.md" in m and "tags" in m for m in found)


def test_file_without_frontmatter_is_reported_but_loader_is_exempt(tmp_path):
    root = tree(tmp_path, healthy({"b.md": "# B\n", "CLAUDE.md": "@index.md\n"}))
    found = messages(root)
    assert any(m.startswith("b.md") and "frontmatter" in m for m in found)
    assert not any(m.startswith("CLAUDE.md") for m in found)


def test_file_not_listed_in_index_is_reported(tmp_path):
    root = tree(tmp_path, healthy({"orphan.md": FRONT + "# O\n"}))
    assert any(m.startswith("orphan.md") and "index.md" in m for m in messages(root))


def test_dead_link_and_dead_anchor_are_reported_with_a_hint(tmp_path):
    body = FRONT + "# A\n\n## Pravila\n\n[x](missing.md) [y](#pravla) [ok](#pravila)\n"
    found = messages(tree(tmp_path, healthy({"a.md": body})))
    assert any("mrtva povezava" in m and "missing.md" in m for m in found)
    assert any("mrtvo sidro" in m and "#pravila" in m for m in found)
    assert not any("#pravila)" in m and "mrtvo sidro → #pravila " in m for m in found)


def test_external_links_and_links_inside_code_are_not_checked(tmp_path):
    body = (
        FRONT
        + "# A\n\n[w](https://example.com/x) `[no](nowhere.md)`\n\n```\n[no](nowhere.md)\n```\n"
    )
    assert messages(tree(tmp_path, healthy({"a.md": body}))) == []


def test_bare_section_refers_to_own_document(tmp_path):
    body = FRONT + "# A\n\n## 1. Prvi\n\nGlej §1 in §7.\n"
    found = messages(tree(tmp_path, healthy({"a.md": body})))
    assert any("§7" in m for m in found)
    assert not any("§1" in m and "§7" not in m for m in found)


def test_named_document_section_is_resolved_in_that_document(tmp_path):
    other = FRONT + "# T\n\n## 2. Odločitve\n"
    ok = FRONT + "# A\n\nTODO.md §2 drži.\n"
    bad = FRONT + "# A\n\nTODO.md §5 ne obstaja.\n"
    index = FRONT + "* [A](a.md)\n* [T](TODO.md)\n"
    good = messages(
        tree(
            tmp_path / "ok", healthy({"a.md": ok, "TODO.md": other, "index.md": index})
        )
    )
    wrong = messages(
        tree(
            tmp_path / "bad",
            healthy({"a.md": bad, "TODO.md": other, "index.md": index}),
        )
    )
    assert good == []
    assert any("TODO.md §5" in m for m in wrong)


def test_section_item_reference_needs_that_numbered_item(tmp_path):
    spec = FRONT + "# S\n\n## 1. Specifikacija\n\n1. prvo\n2. drugo\n"
    index = FRONT + "* [A](a.md)\n* [S](spec.md)\n"
    ok = FRONT + "# A\n\n[spec.md](spec.md) §1 točka 2.\n"
    bad = FRONT + "# A\n\n[spec.md](spec.md) §1 točka 9.\n"
    files = {"spec.md": spec, "index.md": index}
    assert messages(tree(tmp_path / "ok", healthy({**files, "a.md": ok}))) == []
    assert any(
        "točka 9" in m
        for m in messages(tree(tmp_path / "bad", healthy({**files, "a.md": bad})))
    )


def test_main_exit_codes(tmp_path, capsys):
    assert doclinks.main(tree(tmp_path / "ok", healthy())) == 0
    assert (
        doclinks.main(tree(tmp_path / "bad", healthy({"a.md": "# bez frontmattera\n"})))
        == 1
    )
    assert "frontmatter" in capsys.readouterr().out
