"""python_version: ena deklaracija, ta računalnik na njej, brez dobesednih pripetij v delovnih tokovih."""

from agent_tools import python_version as pv


def project(tmp_path, declared=None, workflows=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    if declared is not None:
        (tmp_path / ".python-version").write_text(declared + "\n", encoding="utf-8")
    for name, text in (workflows or {}).items():
        path = tmp_path / ".github" / "workflows" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


USES_FILE = "steps:\n  - uses: actions/setup-python@v5\n    with:\n      python-version-file: .python-version\n"


def test_matching_machine_and_file_based_workflow_pass(tmp_path):
    root = project(tmp_path, "3.11", {"ci.yml": USES_FILE})
    assert pv.version_problems(root, running="3.11") == []


def test_patch_difference_is_not_a_problem(tmp_path):
    root = project(tmp_path, "3.11.15")
    assert pv.version_problems(root, running="3.11.4") == []


def test_machine_on_another_minor_is_reported(tmp_path):
    problems = pv.version_problems(project(tmp_path, "3.11"), running="3.14")
    assert len(problems) == 1
    assert "3.11" in problems[0] and "3.14" in problems[0]


def test_missing_declaration_is_reported(tmp_path):
    problems = pv.version_problems(project(tmp_path), running="3.11")
    assert len(problems) == 1
    assert ".python-version manjka" in problems[0]


def test_literal_pin_in_a_workflow_is_reported_whatever_its_number(tmp_path):
    workflows = {
        "ci.yml": "steps:\n  - uses: actions/setup-python@v5\n    with:\n      python-version: '3.11'\n"
    }
    problems = pv.version_problems(project(tmp_path, "3.11", workflows), running="3.11")
    assert len(problems) == 1
    assert "ci.yml" in problems[0] and "dobesedno" in problems[0]


def test_main_exit_codes(tmp_path):
    running = pv.running_python()
    assert pv.main(project(tmp_path / "ok", running)) == 0
    assert pv.main(project(tmp_path / "bad", "2.7")) == 1
