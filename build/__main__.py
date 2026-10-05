"""`python -m build` — the full gate (stages 1-5), then bundle src/ into dist/.
`python -m build check` — the gate only. `lint` — static analysis only. `test` — every suite only.
"""

import sys
import time

from . import (
    check_environment,
    format_elapsed,
    run_all_stages,
    run_build,
    run_lint,
    run_tests,
)

COMMANDS = {"", "check", "lint", "test"}


def main(argv):
    command = argv[0] if argv else ""
    if command not in COMMANDS:
        print(
            f"Unknown command {command!r}. Use: build [check|lint|test]",
            file=sys.stderr,
        )
        return 2
    start = time.monotonic()
    print(f">>> Running build {command}".rstrip())
    check_environment()
    if command == "lint":
        run_lint()
        verdict = "LINT PASSED"
    elif command == "test":
        run_tests()
        verdict = "TESTS PASSED"
    else:
        stages = run_all_stages()
        verdict = f"build check PASSED: all {len(stages)} stages green"
        if command == "":
            run_build()
            verdict = (
                f"build PASSED: all {len(stages)} stages green, dist/ ready to deploy"
            )
    print(
        f"\n=== Report ===\n\n  ✓ {verdict}\n    TOOK {format_elapsed(time.monotonic() - start)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
