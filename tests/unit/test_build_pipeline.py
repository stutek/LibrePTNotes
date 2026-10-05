"""The stage order and how the gate reacts to a failing step."""

import pytest

import build
from build.testreport import failed_test_ids, failure_exceptions, run_logged


def test_stages_are_numbered_from_one_and_each_has_a_runner():
    numbers = [number for number, _runner, _checks in build.PIPELINE_STAGES]

    assert numbers == list(range(1, len(numbers) + 1))
    assert all(callable(runner) for _number, runner, _checks in build.PIPELINE_STAGES)


def test_every_stage_runs_in_order_and_a_failure_stops_the_ones_after(monkeypatch):
    ran = []

    def stage(number, fails=False):
        def run():
            ran.append(number)
            if fails:
                raise SystemExit(1)
            return 0.0

        return (number, run, ())

    monkeypatch.setattr(build, "PIPELINE_STAGES", (stage(1), stage(2), stage(3)))
    assert build.run_all_stages() == [0.0, 0.0, 0.0]
    assert ran == [1, 2, 3]

    ran.clear()
    monkeypatch.setattr(
        build, "PIPELINE_STAGES", (stage(1), stage(2, fails=True), stage(3))
    )
    with pytest.raises(SystemExit):
        build.run_all_stages()
    assert ran == [1, 2]


def test_concurrent_tasks_all_run_and_the_failures_are_named(capsys):
    ran = []

    def good():
        ran.append("good")

    def bad():
        ran.append("bad")
        raise SystemExit(1)

    def crashes():
        raise RuntimeError("boom")

    failures = build._run_tasks_concurrently(
        {"good": good, "bad": bad, "crashes": crashes}
    )

    assert sorted(failures) == ["bad", "crashes"]
    assert sorted(ran) == ["bad", "good"]


def test_a_step_that_exits_zero_is_not_a_failure():
    def clean():
        raise SystemExit(0)

    assert build._run_tasks_concurrently({"clean": clean}) == []


def test_the_dev_server_port_is_the_one_zap_scans():
    from deploy.local_http_server import dev_server_url

    assert build.ZAP_TARGET == dev_server_url()


PYTEST_OUTPUT = """\
=================================== FAILURES ===================================
E   AssertionError: expected 3
=========================== short test summary info ============================
FAILED tests/e2e/test_a.py::test_one - AssertionError: expected 3
FAILED tests/e2e/test_a.py::test_one - AssertionError: expected 3
ERROR tests/e2e/test_b.py::test_two
"""


def test_a_failure_digest_names_each_failed_test_once_and_surfaces_the_exception():
    assert failed_test_ids(PYTEST_OUTPUT) == [
        "tests/e2e/test_a.py::test_one",
        "tests/e2e/test_b.py::test_two",
    ]
    exceptions, more = failure_exceptions(PYTEST_OUTPUT)
    assert exceptions == ["E   AssertionError: expected 3"]
    assert more == 0


def test_a_logged_run_keeps_its_full_output_and_exit_code(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    run = run_logged(
        ["python3", "-c", "import sys; print('hello'); sys.exit(3)"], "demo"
    )

    assert run.returncode == 3
    assert "hello" in run.output
    assert "hello" in (tmp_path / ".build-reports" / "demo.log").read_text(
        encoding="utf-8"
    )
