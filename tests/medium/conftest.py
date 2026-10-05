"""Medium: komponenta v pravi index.html brez service workerja (predpomnilnik ne vpliva na izid)."""

import pytest


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "service_workers": "block"}
