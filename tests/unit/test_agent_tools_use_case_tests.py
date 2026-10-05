"""use_case_tests: vsaka vrstica sledljivosti navaja test ali pove, zakaj ga ni."""

from agent_tools import use_case_tests as uc

HEAD = "# UC\n\nOpis.\n\n## Sledljivost: obljuba → test\n\n| Obljuba | Test |\n| :--- | :--- |\n"


def test_row_linking_a_test_passes():
    assert (
        uc.problems_in(HEAD + "| Dodam stranko | [t](../tests/e2e/test_flow.py) |\n")
        == []
    )


def test_row_with_a_marked_reason_passes():
    text = (
        HEAD
        + "| Drive | **Ni zgrajeno**: odločitev je odprta |\n| Ura | **Zunaj aplikacije**: telefon |\n"
    )
    assert uc.problems_in(text) == []


def test_row_naming_no_test_and_no_reason_is_reported():
    problems = uc.problems_in(
        HEAD + "| Dodam stranko | deluje |\n| Ok | [t](../tests/x.py) |\n"
    )
    assert len(problems) == 1
    assert "Dodam stranko" in problems[0]


def test_link_outside_tests_does_not_count():
    assert len(uc.problems_in(HEAD + "| Obljuba | [src](../src/app.js) |\n")) == 1


def test_missing_heading_and_empty_table_are_reported():
    assert uc.problems_in("# UC\n\nSamo opis.\n") == ["nima naslova o sledljivosti"]
    assert "nobene vrstice" in uc.problems_in(HEAD)[0]


def test_only_the_table_under_the_heading_is_read():
    text = (
        "| A | B |\n| - | - |\n| izven | tabele |\n\n"
        + HEAD
        + "| Ok | [t](../tests/a.py) |\n\n| X | Y |\n| - | - |\n| spodaj | nič |\n"
    )
    assert uc.problems_in(text) == []


def test_no_use_cases_at_all_is_reported_and_main_exit_codes(tmp_path):
    (tmp_path / "empty").mkdir()
    ok = tmp_path / "ok" / "use_cases"
    ok.mkdir(parents=True)
    (ok / "uc1.md").write_text(HEAD + "| O | [t](../tests/a.py) |\n", encoding="utf-8")
    bad = tmp_path / "bad" / "use_cases"
    bad.mkdir(parents=True)
    (bad / "uc1.md").write_text(HEAD + "| O | nič |\n", encoding="utf-8")
    assert uc.main(tmp_path / "empty") == 1
    assert uc.main(tmp_path / "ok") == 0
    assert uc.main(tmp_path / "bad") == 1
