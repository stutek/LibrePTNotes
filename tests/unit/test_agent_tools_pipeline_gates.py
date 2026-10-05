"""pipeline_gates: ali vsak CI posel zapira objavo in ali potek ponovi vrstni red stopenj."""

from agent_tools import pipeline_gates as pg

BUILD = """
def run_stage_1_parallel():
    tasks = {
        "Lint": run_lint,
        "Docs": run_docs,
    }
    return tasks


PIPELINE_STAGES = (
    (1, run_stage_1_parallel, ()),
    (2, run_stage_2_medium, ("run_medium_tests",)),
    (3, run_stage_3_e2e, ("run_e2e_tests",)),
)
"""

GOOD = """
jobs:
  lint:
    name: Stage 1 · Lint
    steps:
      - uses: actions/checkout@v5
      - run: python -c "from build import run_lint, run_docs; run_lint(); run_docs()"
  medium:
    name: Stage 2 · Medium
    needs: [lint]
    steps:
      - run: python -c "from build import run_medium_tests"
  e2e:
    name: Stage 3 · E2E
    needs: [medium]
    steps:
      - run: python -c "from build import run_e2e_tests"
  deploy:
    name: Post-gate · Deploy
    needs: [e2e]
    steps:
      - run: echo deploy
"""


def project(tmp_path, workflow=GOOD, build=BUILD):
    (tmp_path / "build").mkdir(parents=True, exist_ok=True)
    (tmp_path / "build" / "__init__.py").write_text(build, encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".github" / "workflows" / "deploy.yml").write_text(
        workflow, encoding="utf-8"
    )
    return tmp_path


def failures(root):
    return pg.find_all(root)[0]


def test_well_ordered_and_labelled_workflow_passes(tmp_path):
    problems, jobs, stage_1, stages = pg.find_all(project(tmp_path))
    assert (problems, jobs, stage_1, stages) == ([], 4, 2, 3)


def test_job_nobody_waits_for_is_reported_as_gating_nothing(tmp_path):
    workflow = (
        GOOD
        + "  audit:\n    name: Post-gate · Audit\n    steps:\n      - run: echo audit\n"
    )
    found = failures(project(tmp_path, workflow))
    assert any("2 končnih poslov" in f for f in found)
    assert any("'audit' ničesar ne zapira" in f for f in found)


def test_later_stage_that_does_not_wait_for_the_earlier_one_is_reported(tmp_path):
    workflow = GOOD.replace("    needs: [medium]\n", "    needs: [lint]\n")
    found = failures(project(tmp_path, workflow))
    assert any("'e2e' (stopnja 3) ne počaka na 'medium'" in f for f in found)
    assert any("'medium' ničesar ne zapira" in f for f in found)


def test_job_named_for_the_wrong_stage_or_none_is_reported(tmp_path):
    wrong = GOOD.replace("Stage 2 · Medium", "Stage 3 · Medium")
    unnamed = GOOD.replace("name: Stage 2 · Medium", "name: Srednji testi")
    claims_stage = GOOD.replace("Post-gate · Deploy", "Stage 4 · Deploy")
    assert any(
        "Stage 3" in f and "stopnje 2" in f
        for f in failures(project(tmp_path / "a", wrong))
    )
    assert any(
        "v imenu ni stopnje" in f for f in failures(project(tmp_path / "b", unnamed))
    )
    assert any(
        "ne teče kontrol nobene stopnje" in f
        for f in failures(project(tmp_path / "c", claims_stage))
    )


def test_stage_one_check_that_no_job_runs_is_reported(tmp_path):
    workflow = GOOD.replace(
        "import run_lint, run_docs; run_lint(); run_docs()",
        "import run_lint; run_lint()",
    )
    found = failures(project(tmp_path, workflow))
    assert found == [
        "build.run_docs zapira commit, objave pa ne: noben CI posel je ne požene"
    ]


def test_local_action_before_checkout_is_reported_after_it_is_fine(tmp_path):
    early = GOOD.replace(
        "      - uses: actions/checkout@v5\n",
        "      - uses: ./.github/actions/env\n      - uses: actions/checkout@v5\n",
    )
    late = GOOD.replace(
        "      - uses: actions/checkout@v5\n",
        "      - uses: actions/checkout@v5\n      - uses: ./.github/actions/env\n",
    )
    assert any(
        "pred actions/checkout" in f for f in failures(project(tmp_path / "a", early))
    )
    assert failures(project(tmp_path / "b", late)) == []


def test_missing_build_module_or_workflows_are_reported(tmp_path):
    assert any("build/__init__.py" in f for f in failures(tmp_path))
    (tmp_path / "x" / "build").mkdir(parents=True)
    (tmp_path / "x" / "build" / "__init__.py").write_text(BUILD, encoding="utf-8")
    assert any("workflows" in f for f in failures(tmp_path / "x"))


def test_main_exit_codes(tmp_path):
    assert pg.main(project(tmp_path / "ok")) == 0
    assert (
        pg.main(
            project(
                tmp_path / "bad",
                GOOD.replace(
                    "import run_lint, run_docs; run_lint(); run_docs()",
                    "import run_lint; run_lint()",
                ),
            )
        )
        == 1
    )
