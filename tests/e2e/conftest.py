"""E2E: celotni tokovi s service workerjem. `site` je kopija src/, ki jo test lahko spremeni."""

import hashlib
import json
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from deploy.local_http_server import DEV_SERVER_BASE_PATH

SRC = Path(__file__).resolve().parent.parent.parent / "src"


class Site:
    """Strežnik nad kopijo src/ z živim integrity.json; `corrupt` pokvari hash ene datoteke."""

    def __init__(self, root):
        self.root = root
        self.corrupt = None
        site = self

        class Handler(SimpleHTTPRequestHandler):
            extensions_map = {
                **SimpleHTTPRequestHandler.extensions_map,
                ".js": "text/javascript",
                ".webmanifest": "application/manifest+json",
                ".svg": "image/svg+xml",
            }

            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(root), **kwargs)

            def log_message(self, *_args):
                pass

            def translate_path(self, path):
                return super().translate_path(
                    path.split("?")[0].removeprefix(DEV_SERVER_BASE_PATH.rstrip("/"))
                    or "/"
                )

            def do_GET(self):
                if self.path.split("?")[0] == DEV_SERVER_BASE_PATH + "integrity.json":
                    body = json.dumps(site.catalog()).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(body)
                    return
                super().do_GET()

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://localhost:{self.server.server_port}{DEV_SERVER_BASE_PATH}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def catalog(self):
        files = {}
        for path in sorted(self.root.rglob("*")):
            if path.is_file():
                files[path.relative_to(self.root).as_posix()] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
        if self.corrupt:
            files[self.corrupt] = "0" * 64
        return {"algorithm": "SHA-256", "files": files}

    def edit(self, name, old, new):
        path = self.root / name
        text = path.read_text()
        assert old in text
        path.write_text(text.replace(old, new))

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def site(tmp_path):
    root = tmp_path / "src"
    shutil.copytree(SRC, root)
    instance = Site(root)
    yield instance
    instance.close()
