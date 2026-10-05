"""The static security audits: the shipped <meta> CSP is never weaker than the scanned header, and
user text does not reach an HTML sink unescaped."""

import pytest

from build import run_static_security_checks
from build.frontend_audit import audit_html_sinks, compare_csp, meta_csp
from deploy.local_http_server import SECURITY_HEADERS

POLICY = SECURITY_HEADERS["Content-Security-Policy"]


def index_with(policy_attribute):
    return f'<!doctype html><head><meta http-equiv="Content-Security-Policy" {policy_attribute}></head>'


def test_meta_policy_is_found_whatever_the_attribute_order():
    assert (
        meta_csp(index_with("content=\"default-src 'self'\"")) == "default-src 'self'"
    )
    reordered = (
        '<meta content="default-src \'self\'" http-equiv="Content-Security-Policy">'
    )
    assert meta_csp(reordered) == "default-src 'self'"
    assert meta_csp("<head></head>") is None


def test_an_identical_meta_policy_is_not_weaker_but_frame_ancestors_is_header_only():
    weaker, header_only = compare_csp(POLICY, POLICY)

    assert weaker == []
    assert header_only == ["frame-ancestors"]


def test_a_missing_or_looser_meta_directive_is_weaker():
    missing = POLICY.replace("object-src 'none'", "")
    looser = POLICY.replace(
        "script-src 'self'", "script-src 'self' https://cdn.example"
    )

    assert any("object-src" in problem for problem in compare_csp(POLICY, missing)[0])
    assert any("script-src" in problem for problem in compare_csp(POLICY, looser)[0])


def test_the_dev_server_policy_allows_nothing_but_the_origin_itself():
    # The app is offline-first with no third-party origin: any host appearing here is a regression.
    assert "http" not in POLICY
    assert "'unsafe-inline'" not in POLICY
    assert "'unsafe-eval'" not in POLICY


def test_static_checks_pass_when_the_shipped_policy_matches(
    tmp_path, monkeypatch, capsys
):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "index.html").write_text(
        index_with(f'content="{POLICY}"'), encoding="utf-8"
    )
    (tmp_path / "src" / "app.js").write_text(
        "el.textContent = client.name;\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)

    run_static_security_checks()

    assert "passed" in capsys.readouterr().out


def test_static_checks_fail_when_the_page_ships_no_policy(tmp_path, monkeypatch):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "index.html").write_text(
        "<!doctype html><head></head>", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as stop:
        run_static_security_checks()

    assert stop.value.code == 1


def audit(tmp_path, source):
    (tmp_path / "view.js").write_text(source, encoding="utf-8")
    return audit_html_sinks(str(tmp_path))


def test_unescaped_user_text_in_inner_html_is_reported(tmp_path):
    findings = audit(tmp_path, "row.innerHTML = `<b>${client.name}</b>`;\n")

    assert len(findings) == 1
    assert "client.name" in findings[0][2]


def test_escaped_user_text_and_text_content_are_not_reported(tmp_path):
    assert (
        audit(tmp_path, "row.innerHTML = `<b>${escapeHTML(client.name)}</b>`;\n") == []
    )
    assert audit(tmp_path, "row.textContent = client.name;\n") == []
