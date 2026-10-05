#!/usr/bin/env python3
"""
Local dev server that mirrors the GitHub Pages deployment.

LibrePTNotes is a *project* site served from a sub-path (stutek.github.io/LibrePTNotes/), not a
domain root. Serving src/ at "/" locally (plain `python -m http.server`) would hide exactly the
base-path bugs that only appear under the sub-path, and would let the service worker's scope
(`/LibrePTNotes/`) go untested. This server serves the app under the same sub-path, so local
development and the test suite exercise the real production base.

Behaviour (BASE = "/LibrePTNotes"):
  GET /                        -> 302 redirect to /LibrePTNotes/
  GET /LibrePTNotes            -> 302 redirect to /LibrePTNotes/ (the app uses relative paths, which
                                  only resolve against a trailing slash)
  GET /LibrePTNotes/<file>     -> the matching file from src/, byte for byte
  GET /LibrePTNotes/integrity.json -> a live SHA-256 catalog of src/, same shape as the build's
  anything else                -> 404. There is deliberately NO SPA fallback: the app has no router,
                                  so an unknown path is a real 404, and no <base href> rewriting:
                                  the app uses relative paths and works under any base unchanged.

Run:  python3 -m deploy.local_http_server   (or: python3 -m deploy)
      --port overrides DEV_SERVER_PORT below, which is where the default lives.
"""

import argparse
import hashlib
import io
import json
import os
import threading
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

# The one declaration of the dev-server port and base path. `build` (the ZAP target), the browser
# tests and this module's own default all read them from here, so they cannot drift apart.
PORT_ENV = "LIBREPTNOTES_DEV_SERVER_PORT"
DEV_SERVER_PORT = int(os.environ.get(PORT_ENV) or 8082)

# Where the app is mounted, so a link a test builds matches what the server actually serves.
DEV_SERVER_BASE_PATH = "/LibrePTNotes/"
BASE = DEV_SERVER_BASE_PATH.rstrip("/")


def dev_server_url(path=""):
    """The address the dev server answers on, built from the two declarations above, so no caller
    has to write the port or the base path out again. `path` is appended to the base."""
    return f"http://localhost:{DEV_SERVER_PORT}{DEV_SERVER_BASE_PATH}{path}"


# This file lives in deploy/, so the repo root (which holds src/) is one level up.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")

INTEGRITY_CATALOG_NAME = "integrity.json"

# A reserved path that reports which REVISION of this file the running process was started from.
# A long-lived dev server can silently outlive edits to its own source, and a test run against a
# stale server produces junk results that get blamed on the app. Serving the revision lets tests
# refuse to run against one.
SERVER_REVISION_NAME = "__server_revision__"


def server_revision():
    """SHA-256 of this module's own source, as it was on disk when the process started."""
    with open(os.path.abspath(__file__), "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


# Captured at import, NOT per request: it must report the code this process is actually RUNNING.
RUNNING_REVISION = server_revision()

# Per-request access logging is off by default (see log_message); --verbose brings it back.
VERBOSE = False


def source_fingerprint():
    """A stat-only fingerprint of src/: (path, mtime_ns, size) for every file, no reads. Touching a
    file changes it, which is what lets the catalog be cached without ever going stale."""
    entries = []
    for root, _dirs, names in os.walk(SRC_DIR):
        for name in sorted(names):
            abs_path = os.path.join(root, name)
            stat = os.stat(abs_path)
            entries.append((abs_path, stat.st_mtime_ns, stat.st_size))
    return tuple(sorted(entries))


_catalog_cache = {}
_catalog_lock = threading.Lock()


def build_dev_integrity_catalog():
    """A live SHA-256 integrity catalog of src/, the shape build.generate_integrity_catalog writes
    into dist/, so integrity checks run in local dev exactly as in production.

    Cached on the source fingerprint: computing it hashes every served file while holding the GIL,
    and a parallel browser run would otherwise pay that on every page load."""
    fingerprint = source_fingerprint()
    with _catalog_lock:
        cached = _catalog_cache.get("catalog")
        if cached and cached[0] == fingerprint:
            return cached[1]

    files = {}
    for root, _dirs, names in os.walk(SRC_DIR):
        for name in names:
            abs_path = os.path.join(root, name)
            rel = os.path.relpath(abs_path, SRC_DIR).replace(os.sep, "/")
            with open(abs_path, "rb") as handle:
                files[rel] = hashlib.sha256(handle.read()).hexdigest()
    catalog = {"algorithm": "SHA-256", "files": dict(sorted(files.items()))}
    with _catalog_lock:
        _catalog_cache["catalog"] = (fingerprint, catalog)
    return catalog


# Security headers on every response, so the OWASP ZAP baseline scan audits the app the way a
# hardened host would serve it. GitHub Pages cannot send custom headers, so production's policy is
# only the <meta> CSP in index.html: build.run_static_security_checks fails if that meta policy is
# weaker than this header. The directives a meta tag cannot express (frame-ancestors) are reported
# there as a hosting limitation, not failed.
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "object-src 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": (
        "geolocation=(), camera=(), microphone=(), payment=(), usb=(), "
        "magnetometer=(), gyroscope=(), accelerometer=()"
    ),
    "Cross-Origin-Opener-Policy": "same-origin",
}


class SubPathHandler(SimpleHTTPRequestHandler):
    # HTTP/1.1 for KEEP-ALIVE: the default (1.0) opens a connection per asset. Every response below
    # sets Content-Length, which is what makes persistent connections safe.
    protocol_version = "HTTP/1.1"

    # TCP_NODELAY: without it the separate header and body writes wait on Nagle plus the peer's
    # delayed ACK, a flat ~40ms stall on every request.
    disable_nagle_algorithm = True

    # Suppress the Python/http.server version leak (ZAP "Server Leaks Version Information").
    server_version = "LibrePTNotes-dev"
    sys_version = ""

    # The platform's mime table varies; these are the types the app and its service worker need.
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
        ".mjs": "text/javascript",
        ".webmanifest": "application/manifest+json",
        ".svg": "image/svg+xml",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SRC_DIR, **kwargs)

    def log_message(self, fmt, *args):
        """Silence the per-request access log: lock-contended noise under a parallel test run.
        Errors still surface (log_error is untouched)."""
        if VERBOSE:
            super().log_message(fmt, *args)

    def end_headers(self):
        # Just before the header block closes, so the hardening headers land on every response:
        # redirects, static files and 404s alike.
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        super().end_headers()

    def translate_path(self, path):
        # Strip the /LibrePTNotes prefix, then let the base class map the rest under src/.
        p = urlsplit(path).path
        if p == BASE:
            p = "/"
        elif p.startswith(BASE + "/"):
            p = p[len(BASE) :]
        return super().translate_path(p)

    def _redirect(self, location):
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()
        return None

    def send_head(self):
        raw = urlsplit(self.path).path

        # The domain root and the slash-less base both belong to the app.
        if raw in ("", "/", BASE):
            return self._redirect(BASE + "/")

        # Nothing is served outside the sub-path.
        if not raw.startswith(BASE + "/"):
            self.send_error(HTTPStatus.NOT_FOUND, "App is served under %s/" % BASE)
            return None

        rel = raw[len(BASE) :].lstrip("/")
        if rel == INTEGRITY_CATALOG_NAME:
            return self._send_json(build_dev_integrity_catalog())
        if rel == SERVER_REVISION_NAME:
            return self._send_json({"revision": RUNNING_REVISION})
        return super().send_head()

    def list_directory(self, path):
        # A directory without an index.html is a 404, never a listing: the app has nothing to show
        # there, and a listing is what ZAP's "Directory Browsing" rule flags.
        self.send_error(HTTPStatus.NOT_FOUND)
        return None

    def _send_json(self, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        return io.BytesIO(body)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEV_SERVER_PORT,
        help=f"port to listen on (default: {DEV_SERVER_PORT})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="log every request (off by default: contended noise under a parallel test run)",
    )
    args = parser.parse_args()

    global VERBOSE
    VERBOSE = bool(args.verbose)
    ThreadingHTTPServer.allow_reuse_address = True
    # socketserver's default listen backlog is 5, which a parallel browser run bursts past: a page
    # load then waits in the kernel's SYN queue and times out for no reason the app can explain.
    # Must be a class attribute set before construction: listen() runs in __init__.
    ThreadingHTTPServer.request_queue_size = 128
    server = ThreadingHTTPServer(("", args.port), SubPathHandler)
    print(
        "LibrePTNotes dev server: http://localhost:%d%s/  (root redirects here)"
        % (args.port, BASE)
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
