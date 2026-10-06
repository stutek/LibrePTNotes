"""LibrePTNotes build steps: environment, lint, tests, security scans, and bundling src/ into dist/.

Run from the repository root:
  python -m build           the full gate (stages 1-5), then bundle dist/
  python -m build check     the gate only
  python -m build lint      Ruff, Biome and pip-audit only
  python -m build test      every test suite, without the static analysis

The individual `run_*` steps are also imported by name from .github/workflows/deploy.yml, so a CI job
and the local gate run the very same code. Every step exits non-zero on failure and prints one
verdict line; nothing is printed-and-passed.

This module must import with the standard library alone: the static-audit and build CI jobs run bare
system Python with no `pip install`, so anything third-party is imported inside the step that needs it.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

from build.frontend_audit import audit_html_sinks, compare_csp, meta_csp
from build.testreport import REPORT_DIR, failed_test_ids, print_digest, run_logged
from deploy.local_http_server import (
    DEV_SERVER_BASE_PATH,
    DEV_SERVER_PORT,
    SECURITY_HEADERS,
)

# Python tooling the linters cover. No src/ here: the frontend is checked by Biome below.
PYTHON_LINT_TARGETS = ("build/", "deploy/", "tests/", "agent_tools/")

# src/ is the runtime app; tests/unit_js/ is the only other hand-written JS. Deliberately NOT all of
# tests/: tests/fixtures/ holds frozen backup files that must stay byte-for-byte (biome.json ignores
# them too).
FRONTEND_LINT_TARGETS = ("src/", "tests/unit_js/")

# Records which requirements.txt the venv was last installed from, so an unchanged one is not
# reinstalled. Lives inside .venv/ so deleting the venv correctly forgets it.
REQUIREMENTS_STAMP = os.path.join(".venv", ".requirements-sha256")


def _venv_bin(name):
    """Path of an executable inside the venv, on either OS layout."""
    if os.name == "nt":
        return os.path.join(".venv", "Scripts", name + ".exe")
    return os.path.join(".venv", "bin", name)


def venv_python_path():
    return _venv_bin("python")


def _file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def format_elapsed(seconds):
    minutes, secs = divmod(round(seconds), 60)
    return f"{minutes}m{secs:02d}s" if minutes else f"{secs}s"


def _timed_task(name, fn):
    """Run one pipeline task, always printing its wall-clock time, pass or fail, so a slow gate step
    is visible without re-running it under `time`. Re-raises whatever `fn` raised unchanged."""
    start = time.monotonic()

    def report(mark):
        print(f"    ⏱ {name}: {time.monotonic() - start:.1f}s {mark}")

    try:
        fn()
    except SystemExit as stop:
        report("✓" if stop.code in (0, None) else "✗")
        raise
    except Exception:
        report("✗")
        raise
    report("✓")


# --- Environment ------------------------------------------------------------------------------


def _requirements_changed():
    """True when requirements.txt differs from what the venv was last installed from."""
    if not os.path.exists("requirements.txt"):
        return False
    try:
        with open(REQUIREMENTS_STAMP, encoding="utf-8") as handle:
            return handle.read().strip() != _file_sha256("requirements.txt")
    except OSError:
        return True


def _install_requirements():
    """Install the pinned dependencies, then stamp what was installed. `-q` because pip's default
    output (a line per satisfied requirement) would be most of a green run's output."""
    pip = _venv_bin("pip")
    subprocess.run([pip, "install", "-q", "--upgrade", "pip"], check=True)
    subprocess.run([pip, "install", "-q", "-r", "requirements.txt"], check=True)
    with open(REQUIREMENTS_STAMP, "w", encoding="utf-8") as handle:
        handle.write(_file_sha256("requirements.txt"))


def check_environment():
    """Verifies the venv exists and matches requirements.txt; reinstalls ONLY when it changed.

    It must not run `pip install` on every invocation: that reaches the network, which gives the gate
    a failure mode that has nothing to do with the change under test.
    """
    print(">>> Environment")
    if not os.path.exists(".venv"):
        print(
            "  Virtual environment '.venv' not found. Creating and installing dependencies..."
        )
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
        _install_requirements()
        # A machine that points Playwright at preinstalled browsers must not download another set.
        if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
            subprocess.run([_venv_bin("playwright"), "install", "chromium"], check=True)
    elif _requirements_changed():
        print("  requirements.txt changed — installing dependencies...")
        _install_requirements()
        print("  ✓ Dependencies updated.")
    else:
        print("  ✓ Virtual environment '.venv' verified (dependencies unchanged).")


# --- Vendored tools (Biome, Node, ZAP add-ons) ---------------------------------------------------
#
# Fetched from a third party, pinned to a version and a SHA-256, cached under .venv/ so they are
# downloaded once per environment. Vendored rather than assumed on PATH: contributors and CI run on
# very different machines, and a system install (or its absence) should not decide the gate.

# Two retries after the first try. Long enough to ride out a dropped connection or a CDN edge
# briefly refusing; short enough that a dead host still fails the step instead of hanging it.
_DOWNLOAD_RETRY_DELAYS = (1, 3)


def _with_download_retries(describe, attempt):
    """Run `attempt()`, retrying briefly before letting the failure through.

    A remote closing a connection says nothing about our code, and a single attempt makes the
    pipeline's reliability a function of someone else's worst minute. The retry unit is the whole
    attempt, fetch AND verification: a truncated transfer fails its checksum, so each attempt must
    download again. The final attempt is outside the loop so its exception propagates untouched; the
    caller decides between CI (fail loudly) and local (warn and degrade).
    """
    for delay in _DOWNLOAD_RETRY_DELAYS:
        try:
            return attempt()
        except Exception as error:
            print(f"  ! {describe} failed ({error}); retrying in {delay}s...")
            time.sleep(delay)
    return attempt()


def _download(url, path, timeout=60):
    import urllib.request

    with (
        urllib.request.urlopen(url, timeout=timeout) as response,
        open(path, "wb") as handle,
    ):
        shutil.copyfileobj(response, handle)


def _platform(os_name, arch):
    """(os, 'arm64' | 'x64') for the platforms a contributor or CI runner can be on."""
    if os_name not in ("linux", "darwin", "windows"):
        raise RuntimeError(f"Unsupported OS: {os_name}")
    if "arm64" in arch or "aarch64" in arch:
        return os_name, "arm64"
    if "64" in arch:
        return os_name, "x64"
    raise RuntimeError(f"Unsupported architecture: {arch}")


def _current_platform():
    import platform

    return _platform(platform.system().lower(), platform.machine().lower())


BIOME_VERSION = "1.9.4"
# SHA-256 of the release binary. A platform missing here is size- and magic-checked only.
_BIOME_HASHES = {
    "linux-x64": "ce247fb644999ef52e5111dd6fd6e471019669fc9c4a44b5699721e39b7032c3",
}
_BIOME_MAGIC = {
    "linux": (b"\x7fELF",),
    "windows": (b"MZ",),
    "darwin": (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe"),
}
# A real Biome binary is tens of MB; anything under this is a truncated or error-page download.
_BIOME_MIN_BYTES = 10 * 1024 * 1024


def binary_problem(path, os_name, expected_sha256=None):
    """Why the file at `path` cannot be a good Biome binary, or None when it can be trusted.

    Three independent checks (size, executable signature, checksum): each catches a corruption the
    others miss, and all of them have to pass."""
    if not os.path.exists(path):
        return "missing"
    size = os.path.getsize(path)
    if size < _BIOME_MIN_BYTES:
        return f"too small ({size} bytes), possibly corrupted"
    with open(path, "rb") as handle:
        header = handle.read(4)
    if not header.startswith(_BIOME_MAGIC[os_name]):
        return f"does not look like a {os_name} executable"
    if expected_sha256 and _file_sha256(path) != expected_sha256:
        return "SHA-256 checksum mismatch"
    return None


def ensure_biome_binary():
    """Downloads the pinned Biome binary into .venv/bin if missing or corrupt; returns its path.

    Returns None locally if the download fails (the caller skips the frontend lint with a warning);
    in CI (`CI=true`) the failure is raised, because a gate that silently skips is not a gate."""
    os_name, arch = _current_platform()
    # Biome names Windows binaries "win32-x64.exe".
    suffix = f"win32-{arch}.exe" if os_name == "windows" else f"{os_name}-{arch}"
    biome_path = _venv_bin("biome")
    expected = _BIOME_HASHES.get(f"{os_name}-{arch}")

    if binary_problem(biome_path, os_name, expected) is None:
        return biome_path
    if os.path.exists(biome_path):
        os.remove(biome_path)

    print("  Downloading precompiled Biome binary...")
    url = f"https://github.com/biomejs/biome/releases/download/cli%2Fv{BIOME_VERSION}/biome-{suffix}"

    def fetch():
        os.makedirs(os.path.dirname(biome_path), exist_ok=True)
        _download(url, biome_path, timeout=30)
        if os.name != "nt":
            os.chmod(biome_path, os.stat(biome_path).st_mode | 0o111)
        problem = binary_problem(biome_path, os_name, expected)
        if problem:
            os.remove(biome_path)
            raise ValueError(f"Integrity check failed after download: {problem}.")

    return _fetch_or_degrade(
        "Biome", fetch, biome_path, "Skipping frontend static analysis locally."
    )


def _fetch_or_degrade(what, fetch, result, skip_message):
    """Run a vendoring download; CI raises on failure, a local run warns and returns None."""
    try:
        _with_download_retries(f"{what} download", fetch)
    except Exception as error:
        if os.environ.get("CI") == "true":
            print(f"  ✗ Failed to download/verify {what} in CI: {error}")
            raise
        print(f"  ! Warning: Failed to download/verify {what}: {error}")
        print(f"  ! {skip_message}")
        return None
    print(f"  ✓ {what} downloaded and verified successfully.")
    return result


NODE_VERSION = "24.19.0"
# SHA-256 of the official release ARCHIVE (Node ships an archive, not a single binary), from
# https://nodejs.org/dist/vX.Y.Z/SHASUMS256.txt.
_NODE_ARCHIVE_HASHES = {
    "darwin-arm64": "8294b7aa9b03997481c06babf1e8b270c859358f27da57a11509afe537ac381d",
    "darwin-x64": "d1b5e999db158c62fe8f7267a4476b035d8bd93b1a605bac24a3f0dd166e3316",
    "linux-arm64": "01443c1e1a29e531ccad5a46fefa6df490d2189c49f7955904aecdbb0fe86fdc",
    "linux-x64": "14b342e71204f811bde6153be8e04b62aef63c236fef92b55f9c83154b409647",
    "win-arm64": "8502f4a50b458d4cc38ed8f2001556c2cd239d464920f74017926ccb1e1c157f",
    "win-x64": "57f71ab3652e797d84acddc79c81cc9ff1c6ddb2a1974cdb83f00fee9bff4c73",
}
NODE_INSTALL_DIR = os.path.join(".venv", "node-runtime")


def _node_target(os_name, arch):
    """(dist name like 'linux-x64', archive extension, relative path of the node executable)."""
    name = f"win-{arch}" if os_name == "windows" else f"{os_name}-{arch}"
    ext = {"windows": "zip", "darwin": "tar.gz"}.get(os_name, "tar.xz")
    root = f"node-v{NODE_VERSION}-{name}"
    return (
        name,
        ext,
        os.path.join(root, "node.exe" if os_name == "windows" else "bin/node"),
    )


def _extract_archive(archive_path, ext, target_dir):
    if ext == "zip":
        import zipfile

        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(target_dir)
        return
    import tarfile

    with tarfile.open(archive_path, "r:xz" if ext == "tar.xz" else "r:gz") as archive:
        archive.extractall(target_dir, filter="data")


def ensure_node_binary():
    """Downloads the pinned Node.js runtime into .venv/node-runtime if missing; returns the path of
    its executable, or None locally on a failed download (CI raises).

    tests/unit_js/ needs a real ES-module-capable runtime to import src/ directly, and Node's own
    `node:test` + `node:assert` need no npm packages: no package.json dependencies, no node_modules.
    """
    os_name, arch = _current_platform()
    name, ext, relative = _node_target(os_name, arch)
    node_path = os.path.join(NODE_INSTALL_DIR, relative)
    if os.path.exists(node_path):
        return node_path

    print("  Downloading precompiled Node.js runtime...")
    archive_name = f"node-v{NODE_VERSION}-{name}.{ext}"
    url = f"https://nodejs.org/dist/v{NODE_VERSION}/{archive_name}"
    expected = _NODE_ARCHIVE_HASHES.get(name)

    def fetch():
        os.makedirs(NODE_INSTALL_DIR, exist_ok=True)
        archive_path = os.path.join(NODE_INSTALL_DIR, archive_name)
        _download(url, archive_path, timeout=60)
        if expected and _file_sha256(archive_path) != expected:
            os.remove(archive_path)
            raise ValueError(
                "Integrity check failed after download (SHA-256 mismatch)."
            )
        _extract_archive(archive_path, ext, NODE_INSTALL_DIR)
        os.remove(archive_path)
        if not os.path.exists(node_path):
            raise ValueError(f"Extracted archive did not produce {node_path}.")
        if os_name != "windows":
            os.chmod(node_path, os.stat(node_path).st_mode | 0o111)

    return _fetch_or_degrade(
        "Node.js runtime", fetch, node_path, "Skipping JavaScript tests locally."
    )


# --- Stage 1: lint, scans, unit tests ----------------------------------------------------------
#
# Nothing here rewrites files. The gate only reports; the commands that would fix a finding are
# printed so the owner decides when formatting churn lands in a commit.


def run_python_lint():
    """Python static analysis (Ruff): lint and format check over PYTHON_LINT_TARGETS."""
    print("\n  Running Python Lint & Format check (Ruff)...")
    ruff = _venv_bin("ruff")
    if not os.path.exists(ruff):
        print("  ✗ Ruff not found in the virtual environment.")
        sys.exit(1)
    targets = [path for path in PYTHON_LINT_TARGETS if os.path.isdir(path)]
    # Captured, not streamed: Stage 1 runs tasks in parallel threads, so an uncaptured subprocess
    # would write unattributed output. Surfaced only on failure.
    # Formatting is not a decision, so the gate writes it (as LibrePT does) and names what changed;
    # `git diff` after a run is the record. Lint findings that need judgement still fail.
    fmt = subprocess.run([ruff, "format", *targets], capture_output=True, text=True)
    for line in fmt.stdout.splitlines():
        if "reformatted" in line:
            print(f"    ⓘ {line.strip()}")
    lint = subprocess.run([ruff, "check", *targets], capture_output=True, text=True)
    if lint.returncode != 0 or fmt.returncode != 0:
        print(
            (lint.stdout + fmt.stdout).rstrip() or (lint.stderr + fmt.stderr).rstrip()
        )
        print("  ✗ Python static analysis failed.")
        sys.exit(1)
    print("  ✓ Python static analysis (Ruff) passed.")


def _frontend_stamps():
    """(path -> mtime_ns) of every file Biome may rewrite, so the gate can name what it changed."""
    stamps = {}
    for target in FRONTEND_LINT_TARGETS:
        for root, _dirs, files in os.walk(target):
            for name in files:
                if name.endswith((".js", ".mjs", ".css", ".json")):
                    path = os.path.join(root, name)
                    stamps[path] = os.stat(path).st_mtime_ns
    return stamps


def run_frontend_lint():
    """JS/CSS/JSON static analysis (Biome). Applies the formatting it can fix itself and names every
    file it touched; findings that need judgement are never auto-fixed and still fail the stage."""
    print("\n  Running Frontend Lint & Format (Biome)...")
    biome = ensure_biome_binary()
    if not biome:
        return
    targets = [path for path in FRONTEND_LINT_TARGETS if os.path.isdir(path)]
    before = _frontend_stamps()
    subprocess.run(
        [biome, "check", "--write", *targets], capture_output=True, text=True
    )
    rewritten = [p for p, stamp in _frontend_stamps().items() if before.get(p) != stamp]
    if rewritten:
        print(f"    ⓘ Formatter rewrote {len(rewritten)} file(s):")
        for path in sorted(rewritten):
            print(f"        {path}")
    result = subprocess.run(
        [biome, "check", "--max-diagnostics=200", *targets],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout.rstrip() or result.stderr.rstrip())
        print(
            "  ✗ Frontend static analysis failed (findings above need a human decision)."
        )
        sys.exit(1)
    print("  ✓ Frontend static analysis (Biome) passed.")


def run_security_audit():
    """Dependency vulnerability audit (pip-audit) of the venv."""
    print("\n  Running Dependency Security Audit (pip-audit)...")
    audit = _venv_bin("pip-audit")
    if not os.path.exists(audit):
        print("  ✗ pip-audit not found in the virtual environment.")
        sys.exit(1)
    result = subprocess.run([audit, "--desc"], capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout.rstrip() or result.stderr.rstrip())
        print("  ✗ Security vulnerability audit failed.")
        sys.exit(1)
    print("  ✓ Security vulnerability audit passed.")


def _run_suite(command, log_name, label):
    """Run one test command with its output captured; on failure print the digest and exit with the
    runner's own code. Returns the RunResult on success."""
    run = run_logged(command, log_name)
    if run.returncode != 0:
        print_digest(label, run.output, run.path)
        print(f"  ✗ {label} failed with exit code: {run.returncode}")
        sys.exit(run.returncode)
    print(f"  ✓ {label} passed.")
    return run


def run_unit_tests():
    """Fast Python unit tests (tests/unit/)."""
    print("\n  Running Unit Tests...")
    _run_suite(
        [venv_python_path(), "-m", "pytest", "-q", "--tb=short", "tests/unit/"],
        "unit-tests",
        "Unit tests",
    )


def _run_node_tests(glob, log_name, label):
    node = ensure_node_binary()
    if not node:
        return
    # The explicit glob is what recurses; a bare directory argument misresolves on this Node.
    _run_suite([node, "--test", glob], log_name, label)


def run_javascript_unit_tests():
    """The pure-logic JavaScript suite (tests/unit_js/, security/ excluded) under node:test.

    Needs no browser: Node imports src/ as native ES modules. security/ is gated by
    run_security_tests instead, so a security regression is never reported as a generic failure."""
    print("\n  Running JavaScript Unit Tests (node:test)...")
    _run_node_tests(
        "tests/unit_js/!(security)/**/*.test.mjs",
        "unit-js-tests",
        "JavaScript unit tests",
    )


def run_security_tests():
    """The client-side security suite (tests/unit_js/security/) under node:test.

    Its own gate so the stage name says what broke, and so the class has one directory to list when
    asking "is X covered?". Covers what no other gate reaches: the ZAP baseline is passive and sees
    only the network, while everything here (an imported backup, key handling) never leaves the
    browser."""
    print("\n  Running Security Tests (node:test)...")
    _run_node_tests(
        "tests/unit_js/security/**/*.test.mjs", "security-tests", "Security tests"
    )


def run_unit_coverage_check():
    """Holds pure logic in src/domain/ and src/data/ at its unit-test floor; see
    agent_tools/unit_coverage.py. Runs the JS suite under Node's coverage, so it needs Node."""
    print("\n  Checking unit-test coverage of pure logic...")
    from agent_tools import unit_coverage

    node = ensure_node_binary()
    if node and unit_coverage.main(node) != 0:
        sys.exit(1)


def _run_agent_tool(title, module_name):
    """Run `agent_tools.<module_name>.main()`, which returns a process exit code. The tools are
    imported lazily so `import build` stays reachable from jobs that run on the stdlib alone."""
    import importlib

    print(f"\n  Checking {title}...")
    if importlib.import_module(f"agent_tools.{module_name}").main() != 0:
        sys.exit(1)


def run_doc_graph_check():
    """Markdown cross-references and the index.md graph resolve (agent_tools/doclinks.py)."""
    _run_agent_tool("documentation cross-references", "doclinks")


def run_todo_hygiene_check():
    """TODO.md holds open work only (agent_tools/todo_hygiene.py)."""
    _run_agent_tool("TODO hygiene", "todo_hygiene")


def run_todo_refs_check():
    """No file outside TODO.md points at one of its sections (agent_tools/todo_refs.py)."""
    _run_agent_tool("pointers into TODO", "todo_refs")


def run_module_header_check():
    """A module that names its own path names the right one (agent_tools/module_headers.py)."""
    _run_agent_tool("module self-path headers", "module_headers")


def run_css_token_check():
    """Every `var(--token)` names a property something defines (agent_tools/css_tokens.py)."""
    _run_agent_tool("CSS custom properties", "css_tokens")


def run_ui_string_check():
    """Interface text lives in one place and is Slovenian (agent_tools/ui_strings.py)."""
    _run_agent_tool("interface strings", "ui_strings")


def run_inline_style_check():
    """Appearance is CSS only; code sets classes, not `style` (agent_tools/inline_styles.py)."""
    _run_agent_tool("styles written in code", "inline_styles")


def run_import_layer_check():
    """The import graph flows one way (agent_tools/import_layers.py)."""
    _run_agent_tool("import layering", "import_layers")


def run_complexity_check():
    """Cyclomatic complexity ceiling for the frontend JS (agent_tools/complexity.py)."""
    _run_agent_tool("frontend cyclomatic complexity", "complexity")


def run_test_assertion_check():
    """Tests assert behaviour, not mechanics (agent_tools/test_assertions.py)."""
    _run_agent_tool("test assertions (behaviour, not mechanics)", "test_assertions")


def run_use_case_test_check():
    """Every use case points each promise at a test (agent_tools/use_case_tests.py)."""
    _run_agent_tool("use-case traceability", "use_case_tests")


def run_catalog_coverage_check():
    """The module catalog still describes the tree (agent_tools/catalog_coverage.py)."""
    _run_agent_tool("module catalog coverage", "catalog_coverage")


def run_pipeline_gate_check():
    """Every CI job gates the deploy and the workflow reproduces PIPELINE_STAGES
    (agent_tools/pipeline_gates.py)."""
    _run_agent_tool("CI pipeline gating", "pipeline_gates")


def run_python_version_check():
    """One Python declaration (.python-version), and this machine is on it
    (agent_tools/python_version.py)."""
    _run_agent_tool("the Python version declaration", "python_version")


def run_docs_render_check():
    """A generated documentation page is not out of date with its Markdown source
    (agent_tools/render_docs.py)."""
    _run_agent_tool("generated documentation pages", "render_docs")


def _csp_problems():
    """(weaker, header_only): where the SHIPPED <meta> CSP is weaker than the SCANNED header."""
    index_path = os.path.join("src", "index.html")
    if not os.path.exists(index_path):
        return [f"{index_path} not found"], []
    with open(index_path, encoding="utf-8") as handle:
        meta = meta_csp(handle.read())
    if meta is None:
        return ["src/index.html has no <meta http-equiv=Content-Security-Policy>"], []
    return compare_csp(SECURITY_HEADERS["Content-Security-Policy"], meta)


def check_csp_parity():
    """(problems, notes) — is the shipped policy as strong as the scanned one?

    ZAP validates the dev server's real HTTP headers; GitHub Pages cannot send headers at all, so
    production's policy is only the <meta> tag. Hardening the header while leaving <meta> behind
    would buy a green scan and ship nothing."""
    weaker, header_only = _csp_problems()
    notes = []
    if header_only:
        notes.append(
            f"{', '.join(header_only)} cannot be expressed in <meta>, so production goes "
            "without (GitHub Pages sends no custom headers)"
        )
    return weaker, notes


def check_html_sinks():
    """User-controlled text reaching innerHTML unescaped (see build/frontend_audit.py)."""
    return [
        f"{path}:{line}  ${{{expression}}} — use textContent, or escape it; an imported backup is untrusted"
        for path, line, expression in audit_html_sinks("src")
    ]


STATIC_SECURITY_CHECKS = (
    ("CSP parity (shipped <meta> vs scanned header)", check_csp_parity),
    ("HTML-sink escaping audit", lambda: (check_html_sinks(), [])),
)


def run_static_security_checks():
    """Run every static security check, reporting each by name. Runs them ALL before failing: one
    run should list everything that is wrong, not stop at the first problem."""
    print("\n  Running Static Security Audits...")
    failures = []
    for name, check in STATIC_SECURITY_CHECKS:
        problems, notes = check()
        if problems:
            print(f"    ✗ {name}")
            for problem in problems:
                print(f"        • {problem}")
            failures.append(name)
        else:
            print(f"    ✓ {name}")
        for note in notes:
            print(f"        note: {note}")
    if failures:
        print(f"  ✗ Static security audits failed: {', '.join(failures)}")
        sys.exit(1)
    print("  ✓ Static security audits passed.")


def _run_tasks_concurrently(tasks):
    """Run a {display name: callable} mapping in parallel; return the names that failed."""
    import concurrent.futures

    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        future_to_name = {
            executor.submit(_timed_task, name, task): name
            for name, task in tasks.items()
        }
        for future in concurrent.futures.as_completed(future_to_name):
            name = future_to_name[future]
            try:
                future.result()
            except SystemExit as stop:
                if stop.code != 0:
                    failures.append(name)
            except Exception as error:
                print(f"  ✗ Task '{name}' raised exception: {error}")
                failures.append(name)
    return failures


def run_stage_1_parallel():
    """Stage 1: every lint, scan and fast check, concurrently. None of them writes a file, so there
    is no formatting phase to order first."""
    print(
        "\n=== Stage 1: Linting, Security Scans & Unit Tests (Parallel Execution) ==="
    )
    # `agent_tools/pipeline_gates.py` reads this table as text to know which checks Stage 1 holds,
    # so keep the `"Name": run_function,` shape.
    tasks = {
        "Python Lint (Ruff)": run_python_lint,
        "Frontend Lint (Biome)": run_frontend_lint,
        "Dependency Security Scan (pip-audit)": run_security_audit,
        "Unit Tests": run_unit_tests,
        "JavaScript Unit Tests": run_javascript_unit_tests,
        "Security Tests": run_security_tests,
        "Static Security Audits": run_static_security_checks,
        "Documentation Graph": run_doc_graph_check,
        "TODO Hygiene": run_todo_hygiene_check,
        "TODO Pointers": run_todo_refs_check,
        "Module Catalog Coverage": run_catalog_coverage_check,
        "Module Headers": run_module_header_check,
        "CSS Tokens": run_css_token_check,
        "UI Strings": run_ui_string_check,
        "Inline Styles": run_inline_style_check,
        "Import Layering": run_import_layer_check,
        "Pipeline Gating": run_pipeline_gate_check,
        "Python Version": run_python_version_check,
        "Cyclomatic Complexity": run_complexity_check,
        "Test Assertions": run_test_assertion_check,
        "Use-Case Traceability": run_use_case_test_check,
        "Unit Coverage": run_unit_coverage_check,
        "Rendered Docs": run_docs_render_check,
    }
    start = time.monotonic()
    failures = _run_tasks_concurrently(tasks)
    elapsed = time.monotonic() - start
    if failures:
        print(f"\n  ✗ Stage 1 failed in tasks: {', '.join(failures)} ({elapsed:.1f}s)")
        print(f"    Digests above; full runner logs in {REPORT_DIR}/")
        sys.exit(1)
    print(f"\n  ✓ Stage 1 completed cleanly! ({elapsed:.1f}s)")
    return elapsed


# --- Stages 2-5: browser suites and ZAP ----------------------------------------------------------


def _playwright_worker_count():
    """Half the visible cores. A browser per core starves headless Chromium's own process fan-out
    and bursts the dev server's connection queue, which shows up as `Page.goto` timeouts that have
    nothing to do with the app. `os.cpu_count()` can be None in a container; fall back to serial."""
    return max(1, (os.cpu_count() or 2) // 2)


def _run_browser_suite(directory, log_name, label, workers=None):
    """Run a Playwright pytest directory in parallel. A failure fails the build outright, with no
    automatic re-run: "passed on retry" is not evidence a test is reliable, so a flake is fixed at
    its root instead. `--tb=long` plus build/testreport.py's digest (which prints the raised
    exception first) makes a failure diagnosable without a second run."""
    run = run_logged(
        [
            venv_python_path(),
            "-m",
            "pytest",
            "-n",
            str(workers or _playwright_worker_count()),
            "-q",
            "--tb=long",
            # A hung test must fail by name, not hold the stage until the runner's 6 h limit
            # (run 19 of the Pages workflow did exactly that, with no output to say which test).
            "--timeout=90",
            # The signal method cannot interrupt a worker stuck inside the Playwright driver; the
            # thread method dumps every stack and kills the worker, so the hung test is named.
            "--timeout-method=thread",
            directory,
        ],
        log_name,
    )
    if run.returncode == 0:
        print(f"  ✓ {label} passed.")
        return
    print_digest(label, run.output, run.path)
    failed = failed_test_ids(run.output)
    print(f"  ✗ {label} failed:")
    for test_id in failed:
        print(f"      • {test_id}")
    if run.returncode == 5:
        print(
            f"    (pytest collected no tests in {directory}: an empty suite is not a pass)"
        )
    elif not failed:
        print(
            f"    (runner itself died: collection error or crashed worker; see {run.path})"
        )
    print(f"    Full log: {run.path}")
    sys.exit(run.returncode)


def run_medium_tests():
    """Medium-tier suite (tests/medium/): one component mounted in a real browser page, no router,
    IndexedDB or service worker around it."""
    print("\n  Running Medium Component Tests (parallel)...")
    _run_browser_suite("tests/medium/", "medium-parallel", "Medium component tests")


def run_e2e_tests(workers=None):
    """Full-flow browser suite (tests/e2e/) against the dev server under /LibrePTNotes/."""
    print("\n  Running E2E Browser Tests (parallel)...")
    _run_browser_suite("tests/e2e/", "e2e-parallel", "E2E browser tests", workers)


def run_regression_tests():
    """Stage 4: tests/regression/, the frozen backup files. A backup written by an older version
    must still restore, so these files are never edited: a failure here means a promise to existing
    users broke, which is a different sentence from "the work in hand does not hold yet"."""
    print("\n  Running Regression Suite (frozen backups)...")
    _run_browser_suite("tests/regression/", "regression", "Regression suite")


ZAP_PORT = DEV_SERVER_PORT
ZAP_TARGET = f"http://localhost:{DEV_SERVER_PORT}{DEV_SERVER_BASE_PATH}"
ZAP_ADDONS_DIR = os.path.join(".venv", "zap-addons")
ZAP_TIMEOUT_SECONDS = 1200

# The passive-scan add-ons the scanner image would otherwise try to fetch at startup. Without them
# six passive rules (including Source Code Disclosure) are silently skipped, so they are vendored,
# pinned and verified like Biome and Node.
_ZAP_ADDONS = {
    "pscanrulesBeta-beta-50.zap": (
        "https://github.com/zaproxy/zap-extensions/releases/download/pscanrulesBeta-v50/pscanrulesBeta-beta-50.zap",
        "a979f7cd5d8be10e0338b417e006ec1e2f6ec79101010d570ddb5199892e921b",
    ),
    "commonlib-release-1.43.0.zap": (
        "https://github.com/zaproxy/zap-extensions/releases/download/commonlib-v1.43.0/commonlib-release-1.43.0.zap",
        "f1c46d6c65434a2a54307065b558a87121eaa5b9b6bc6cfb10bf230b6335d1f5",
    ),
}


def ensure_zap_addons():
    """Vendors the pinned ZAP add-ons into .venv/zap-addons/, downloading only what is missing or
    checksum-mismatched. Returns the absolute directory to mount into the scanner, or None."""
    os.makedirs(ZAP_ADDONS_DIR, exist_ok=True)
    for name, (url, expected) in _ZAP_ADDONS.items():
        path = os.path.join(ZAP_ADDONS_DIR, name)
        if os.path.exists(path) and _file_sha256(path) == expected:
            continue
        if os.path.exists(path):
            os.remove(
                path
            )  # corrupt or superseded: never scan with an unverified rule set
        print(f"  Downloading ZAP add-on {name}...")

        def fetch(url=url, path=path, name=name, expected=expected):
            _download(url, path)
            actual = _file_sha256(path)
            if actual != expected:
                os.remove(path)
                raise ValueError(
                    f"SHA-256 mismatch for {name}\n    Expected: {expected}\n    Got:      {actual}"
                )

        try:
            _with_download_retries(f"ZAP add-on {name} download", fetch)
        except Exception as error:
            print(f"  ✗ Failed to download/verify ZAP add-on {name}: {error}")
            return None
    return os.path.abspath(ZAP_ADDONS_DIR)


def _is_port_open(port):
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("localhost", port)) == 0


def _start_zap_target():
    """Serve the app on ZAP_PORT if nothing does, and return the process we started (or None).

    A scan that reaches nothing exits "clean" and gives false assurance, so the target is made to
    exist rather than assumed. Waits up to ~10s for it to bind."""
    if _is_port_open(ZAP_PORT):
        return None
    process = subprocess.Popen(
        [sys.executable, "-m", "deploy.local_http_server", "--port", str(ZAP_PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(100):
        if _is_port_open(ZAP_PORT):
            return process
        time.sleep(0.1)
    process.terminate()
    return None


def run_owasp_zap_scan():
    """Runs the OWASP ZAP baseline scan against the dev server and FAILS the build on any finding.

    The container runs on the host network so it reaches the app on ZAP_PORT; alerts are triaged by
    deploy/zap/zap-baseline.conf (each ignore justified there); a non-zero ZAP exit (1 FAIL, 2 WARN,
    3 scan error or unreachable) fails the build. Nothing is printed-and-passed.
    """
    print("\n  Running OWASP ZAP Security Scan...")
    docker = shutil.which("docker")
    if not docker:
        print("  ✗ OWASP ZAP requires Docker, which is not available on PATH.")
        sys.exit(1)
    if subprocess.run([docker, "info"], capture_output=True).returncode != 0:
        print("  ✗ OWASP ZAP requires Docker, but the Docker daemon is not reachable.")
        sys.exit(1)

    server = _start_zap_target()
    try:
        if not _is_port_open(ZAP_PORT):
            print(
                f"  ✗ OWASP ZAP target {ZAP_TARGET} is not reachable: nothing to scan."
            )
            sys.exit(1)
        addons = ensure_zap_addons()
        if not addons:
            print(
                "  ✗ ZAP add-ons could not be vendored: refusing to scan with an incomplete rule set."
            )
            sys.exit(1)
        _run_zap_container(docker, addons)
    finally:
        if server:
            server.terminate()


def _run_zap_container(docker, addons_dir):
    print("    - Launching OWASP ZAP container baseline scan (host network)...")
    container = "libreptnotes-zap-baseline"
    conf_dir = os.path.join(os.path.abspath("deploy"), "zap")
    try:
        # fmt: off
        run = run_logged(
            [
                docker, "run", "--rm", "--name", container, "--network", "host",
                "-v", f"{conf_dir}:/zap/wrk:ro",
                "-v", f"{addons_dir}:/home/zap/.ZAP/plugin",
                "zaproxy/zap-stable",
                "zap-baseline.py", "-t", ZAP_TARGET, "-c", "zap-baseline.conf", "-z", "-silent",
            ],
            "zap-baseline",
            timeout=ZAP_TIMEOUT_SECONDS,
        )
        # fmt: on
    except subprocess.TimeoutExpired as expired:
        subprocess.run([docker, "stop", container], capture_output=True)
        print(
            f"  ✗ OWASP ZAP scan did not finish within {ZAP_TIMEOUT_SECONDS}s and was killed. "
            f"Partial output: {getattr(expired, 'log_path', REPORT_DIR)}. Check host load and "
            "Docker's own network access before assuming the app is at fault."
        )
        sys.exit(1)
    if run.returncode == 0:
        print(
            f"  ✓ OWASP ZAP baseline scan passed cleanly (WARN-NEW: 0). Log: {run.path}"
        )
        return
    print("\n".join(run.output.strip().splitlines()[-40:]))
    print(f"  ✗ OWASP ZAP scan failed (exit {run.returncode}). Full log: {run.path}")
    sys.exit(1)


def _run_single_task_stage(number, title, task_name, task):
    """A stage that is one task, gated on the previous stage by the caller's ordering."""
    print(f"\n=== Stage {number}: {title} ===")
    start = time.monotonic()
    _timed_task(task_name, task)
    elapsed = time.monotonic() - start
    print(f"\n  ✓ Stage {number} completed cleanly! ({elapsed:.1f}s)")
    return elapsed


def run_stage_2_medium():
    return _run_single_task_stage(
        2, "Medium Component Tests", "Medium Component Tests", run_medium_tests
    )


def run_stage_3_e2e():
    return _run_single_task_stage(
        3, "E2E Browser Tests", "E2E Browser Tests", run_e2e_tests
    )


def run_stage_4_regression():
    return _run_single_task_stage(
        4, "Regression Suite (frozen backups)", "Regression Suite", run_regression_tests
    )


def run_stage_5_zap():
    return _run_single_task_stage(
        5, "OWASP ZAP Security Scan", "OWASP ZAP Scan", run_owasp_zap_scan
    )


# The ONE declaration of the stage order. `run_all_stages` walks it, and agent_tools/pipeline_gates.py
# reads it as text and fails Stage 1 if .github/workflows/deploy.yml does not reproduce it. Each row:
# (number, runner, the `run_*` checks the stage holds). Stage 1's row is empty on purpose: its checks
# are declared in run_stage_1_parallel's own `tasks` table, and reading them twice would be the
# duplication the checker exists to prevent.
PIPELINE_STAGES = (
    (1, run_stage_1_parallel, ()),
    (2, run_stage_2_medium, ("run_medium_tests",)),
    (3, run_stage_3_e2e, ("run_e2e_tests",)),
    (4, run_stage_4_regression, ("run_regression_tests",)),
    (5, run_stage_5_zap, ("run_owasp_zap_scan",)),
)


def run_all_stages():
    """Every stage in order, each starting only if the previous one was clean (a failing stage
    exits the process). Returns each stage's seconds."""
    return [runner() for _, runner, _ in PIPELINE_STAGES]


def run_lint():
    """All static analysis: Ruff, Biome, pip-audit."""
    run_python_lint()
    run_frontend_lint()
    run_security_audit()


def run_tests():
    """Every test suite: unit, JavaScript, security, medium, e2e, regression."""
    run_unit_tests()
    run_javascript_unit_tests()
    run_security_tests()
    run_medium_tests()
    run_e2e_tests()
    run_regression_tests()


# --- Bundle ------------------------------------------------------------------------------------

INTEGRITY_CATALOG_NAME = "integrity.json"


def stamp_build_version(dist_dir):
    """Write dist/version.js with the short commit SHA and UTC build time (the build stamp the app
    shows). Written, not patched: src/version.js carries a placeholder for local development."""
    try:
        commit = (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except (OSError, subprocess.CalledProcessError):
        commit = "local"
    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    with open(os.path.join(dist_dir, "version.js"), "w", encoding="utf-8") as handle:
        handle.write(
            f'export const BUILD_INFO = {{ commit: "{commit}", builtAt: "{built_at}" }};\n'
        )
    print(f"  Stamped build {commit} ({built_at})")
    stamp_cache_version(dist_dir)


def stamp_cache_version(dist_dir):
    """Patch dist/sw.js `CACHE_VERSION` to the commit count, so every published build names a new
    cache and the browser sees a changed worker. A hand-kept number is one nobody remembers to raise,
    and the update bar then never appears. No history (shallow clone) leaves the checked-in number."""
    try:
        count = int(
            subprocess.check_output(
                ["git", "rev-list", "--count", "HEAD"], stderr=subprocess.DEVNULL
            )
        )
    except (OSError, ValueError, subprocess.CalledProcessError):
        return
    path = os.path.join(dist_dir, "sw.js")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    patched = re.sub(
        r"const CACHE_VERSION = \d+;", f"const CACHE_VERSION = {count};", text
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(patched)
    print(f"  Cache version {count}")


def generate_integrity_catalog(dist_dir, catalog_name=INTEGRITY_CATALOG_NAME):
    """Write dist/integrity.json: the SHA-256 of every bundled file, keyed by its dist-root-relative
    POSIX path. Run LAST, after every other mutation, so the hashes match the exact bytes that ship.
    The catalog cannot hash itself, so it is excluded. Returns the {path: hash} map."""
    files = {}
    for root, _dirs, names in os.walk(dist_dir):
        for name in names:
            path = os.path.join(root, name)
            rel = os.path.relpath(path, dist_dir).replace(os.sep, "/")
            if rel != catalog_name:
                files[rel] = _file_sha256(path)
    catalog = {"algorithm": "SHA-256", "files": dict(sorted(files.items()))}
    with open(os.path.join(dist_dir, catalog_name), "w", encoding="utf-8") as handle:
        json.dump(catalog, handle, indent=2)
        handle.write("\n")
    print(f"  Wrote {catalog_name} ({len(files)} files hashed, SHA-256)")
    return files


def run_build(dist_dir="dist", src_dir="src"):
    """Bundle src/ into dist/: copy, stamp the version, add .nojekyll, then write integrity.json.

    No <base href> rewriting and no 404.html: the app has no router and uses relative paths, so the
    copy works under any base path unchanged."""
    print("\n>>> Running Build & Bundle Step...")
    if not os.path.isdir(src_dir):
        print(f"  ✗ {src_dir}/ not found.")
        sys.exit(1)
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    shutil.copytree(src_dir, dist_dir)
    stamp_build_version(dist_dir)
    # Disable Jekyll processing on the published site.
    open(os.path.join(dist_dir, ".nojekyll"), "w", encoding="utf-8").close()
    generate_integrity_catalog(dist_dir)
    print(f"  ✓ Build complete. Bundle stored in: {os.path.abspath(dist_dir)}")
