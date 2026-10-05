"""todo_hygiene: številčenje razdelkov in kratke zaprte točke v §3."""

from agent_tools import todo_hygiene

HEAD = '---\ntype: todo\ntitle: "T"\ndescription: "D"\ntags: [a]\n---\n\n# T\n\n'


def todo(tmp_path, body):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "TODO.md").write_text(HEAD + body, encoding="utf-8")
    return tmp_path


def messages(root):
    return [m for _rel, _n, m in todo_hygiene.find_all(root)]


GOOD = "## 1. Spec\n\ntekst\n\n## 2. Odločitve\n\n- razlog\n\n## 3. Odprto\n\n- [x] **Narejeno** (2026-10-05): izid.\n- [ ] **Odprto** (2026-10-05): kaj manjka.\n"


def test_well_formed_todo_passes(tmp_path):
    assert messages(todo(tmp_path, GOOD)) == []


def test_gap_or_duplicate_in_section_numbers_is_reported(tmp_path):
    gap = GOOD.replace("## 2. Odločitve", "## 4. Odločitve")
    duplicate = GOOD.replace("## 2. Odločitve", "## 1. Odločitve")
    assert any("pričakovan 2" in m for m in messages(todo(tmp_path / "gap", gap)))
    assert any("pričakovan 2" in m for m in messages(todo(tmp_path / "dup", duplicate)))


def test_closed_item_with_a_continuation_line_is_reported(tmp_path):
    body = GOOD.replace(
        "izid.\n", "izid.\n  Dolga razlaga, ki sodi v razdelek odločitev.\n"
    )
    assert any("zaprta točka" in m for m in messages(todo(tmp_path, body)))


def test_long_closed_item_is_reported_but_long_open_item_is_not(tmp_path):
    long_text = "x" * 400
    closed = GOOD.replace("izid.", long_text)
    opened = GOOD.replace("kaj manjka.", long_text)
    assert any("zaprta točka" in m for m in messages(todo(tmp_path / "c", closed)))
    assert messages(todo(tmp_path / "o", opened)) == []


def test_bullet_without_checkbox_or_with_other_mark_is_reported(tmp_path):
    body = GOOD + "- brez polja\n- [~] delno\n- [X] velika\n"
    found = [m for m in messages(todo(tmp_path, body)) if "ni jasno" in m]
    assert len(found) == 3


def test_missing_open_section_and_missing_file(tmp_path):
    only_two = "## 1. Spec\n\n## 2. Odločitve\n"
    assert any("manjka razdelek" in m for m in messages(todo(tmp_path / "a", only_two)))
    (tmp_path / "empty").mkdir()
    assert any("ni" in m for m in messages(tmp_path / "empty"))


def test_main_exit_codes(tmp_path):
    assert todo_hygiene.main(todo(tmp_path / "ok", GOOD)) == 0
    assert (
        todo_hygiene.main(todo(tmp_path / "bad", GOOD.replace("## 3.", "## 5."))) == 1
    )
