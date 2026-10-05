"""Skupno ogrodje brskalniških testov (medium, e2e, regression).

Strežnik je deploy.local_http_server (isti kot v razvoju: obseg /LibrePTNotes/, živ integrity.json,
varnostne glave), po en na delavca xdist na lastnih vratih. Vsak test dobi svoj brskalniški kontekst,
torej svoj IndexedDB, predpomnilnik in service worker. Telefon: 390x780 z dotikom.
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from deploy.local_http_server import (  # noqa: E402
    DEV_SERVER_BASE_PATH,
    DEV_SERVER_PORT,
)

PHONE = {
    "viewport": {"width": 390, "height": 780},
    "is_mobile": True,
    "has_touch": True,
    "device_scale_factor": 2,
    "locale": "sl-SI",
    "timezone_id": "Europe/Ljubljana",
}


def _worker_index():
    worker = os.environ.get("PYTEST_XDIST_WORKER", "gw0")
    return int(worker.removeprefix("gw"))


def _wait_for_port(port, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.05)
    raise RuntimeError(f"dev strežnik se ni zagnal na vratih {port}")


@pytest.fixture(scope="session")
def server_url():
    """Naslov aplikacije (z zaključno poševnico); strežnik teče, dokler traja seja delavca."""
    port = DEV_SERVER_PORT + 10 + _worker_index()
    process = subprocess.Popen(
        [sys.executable, "-m", "deploy.local_http_server", "--port", str(port)],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
    )
    try:
        _wait_for_port(port)
        yield f"http://localhost:{port}{DEV_SERVER_BASE_PATH}"
    finally:
        process.terminate()
        process.wait(timeout=10)


@pytest.fixture(scope="session")
def base_url(server_url):
    return server_url


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, **PHONE}
