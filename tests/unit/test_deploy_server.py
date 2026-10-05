"""The dev server mirrors GitHub Pages: the app lives under /LibrePTNotes/, files are served byte for
byte, an unknown path is a real 404, and every response carries the security headers."""

import hashlib
import http.client
import json
import pathlib
import threading
from http.server import ThreadingHTTPServer

import pytest

from deploy import local_http_server as server


@pytest.fixture(scope="module")
def port():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.SubPathHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd.server_address[1]
    httpd.shutdown()
    httpd.server_close()


def get(port, path, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    connection.request("GET", path, headers=headers or {})
    response = connection.getresponse()
    body = response.read()
    connection.close()
    return response, body


def test_the_domain_root_and_the_slashless_base_redirect_to_the_app(port):
    for path in ("/", "/LibrePTNotes"):
        response, _ = get(port, path)
        assert response.status == 302
        assert response.getheader("Location") == "/LibrePTNotes/"


def test_the_app_is_served_unchanged_under_the_base_path(port):
    response, body = get(port, "/LibrePTNotes/")

    assert response.status == 200
    assert response.getheader("Content-Type").startswith("text/html")
    assert body == (pathlib.Path(server.SRC_DIR) / "index.html").read_bytes()
    assert b"<base" not in body


def test_script_and_manifest_have_the_types_a_browser_requires(port):
    script, _ = get(port, "/LibrePTNotes/sw.js")
    manifest, _ = get(port, "/LibrePTNotes/manifest.webmanifest")

    assert script.getheader("Content-Type").startswith("text/javascript")
    assert manifest.getheader("Content-Type").startswith("application/manifest+json")


def test_unknown_paths_and_paths_outside_the_base_are_404_not_the_app_shell(port):
    for path in (
        "/LibrePTNotes/nothing",
        "/LibrePTNotes/no/such/route",
        "/elsewhere/index.html",
    ):
        response, body = get(port, path)
        assert response.status == 404
        assert b'id="view"' not in body  # not the app shell: there is no SPA fallback


def test_a_directory_is_never_listed(port):
    response, body = get(port, "/LibrePTNotes/ui/")

    assert response.status == 404
    assert b"Directory listing" not in body


def test_a_path_cannot_climb_out_of_src(port):
    response, body = get(port, "/LibrePTNotes/../AGENT_RULES.md")

    assert response.status in (301, 302, 400, 404)
    assert b"pravila agentov" not in body
    response, body = get(port, "/LibrePTNotes/%2e%2e/AGENT_RULES.md")
    assert b"pravila agentov" not in body


def test_the_live_integrity_catalog_matches_what_is_served(port):
    response, body = get(port, "/LibrePTNotes/integrity.json")
    catalog = json.loads(body)

    assert response.status == 200
    assert catalog["algorithm"] == "SHA-256"
    assert "index.html" in catalog["files"]
    for rel in ("index.html", "sw.js"):
        _, served = get(port, f"/LibrePTNotes/{rel}")
        assert catalog["files"][rel] == hashlib.sha256(served).hexdigest()


def test_the_running_revision_is_reported_so_tests_can_refuse_a_stale_server(port):
    _, body = get(port, "/LibrePTNotes/__server_revision__")

    assert json.loads(body)["revision"] == server.server_revision()


def test_every_response_carries_the_security_headers_including_errors_and_redirects(
    port,
):
    for path in ("/", "/LibrePTNotes/", "/LibrePTNotes/nothing"):
        response, _ = get(port, path)
        for name, value in server.SECURITY_HEADERS.items():
            assert response.getheader(name) == value


def test_the_server_does_not_announce_its_python_version(port):
    response, _ = get(port, "/LibrePTNotes/")

    assert "Python" not in (response.getheader("Server") or "")


def test_the_dev_server_url_is_built_from_the_declared_port_and_base():
    assert (
        server.dev_server_url("x")
        == f"http://localhost:{server.DEV_SERVER_PORT}/LibrePTNotes/x"
    )
