"""Vendored tools (Biome, Node, ZAP add-ons): a cached good copy is reused, a corrupt or tampered one
is replaced, and a failed download degrades locally but fails loudly in CI. No network is touched:
the download function is replaced."""

import hashlib
import io
import os
import pathlib
import tarfile

import pytest

import build

ELF = b"\x7fELF"


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(build, "_current_platform", lambda: ("linux", "x64"))
    monkeypatch.setattr(build.time, "sleep", lambda _seconds: None)
    monkeypatch.delenv("CI", raising=False)
    # Hashes of the real release do not apply to the stand-in files below.
    monkeypatch.setattr(build, "_BIOME_HASHES", {})
    monkeypatch.setattr(build, "_BIOME_MIN_BYTES", 64)


def fake_biome(path, payload=ELF + b"\0" * 100):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def test_a_good_cached_biome_is_reused_without_downloading(monkeypatch):
    fake_biome(pathlib.Path(".venv/bin/biome"))
    monkeypatch.setattr(build, "_download", lambda *a, **k: pytest.fail("downloaded"))

    assert build.ensure_biome_binary() == ".venv/bin/biome"


def test_a_corrupt_cached_biome_is_replaced_by_a_verified_download(monkeypatch):
    fake_biome(pathlib.Path(".venv/bin/biome"), b"<html>error page</html>")
    monkeypatch.setattr(
        build, "_download", lambda url, path, timeout=60: fake_biome(pathlib.Path(path))
    )

    path = build.ensure_biome_binary()

    assert pathlib.Path(path).read_bytes().startswith(ELF)


def test_a_download_that_fails_verification_is_not_kept(monkeypatch):
    monkeypatch.setattr(
        build,
        "_download",
        lambda url, path, timeout=60: fake_biome(pathlib.Path(path), b"nope"),
    )

    assert build.ensure_biome_binary() is None
    assert not pathlib.Path(".venv/bin/biome").exists()


def test_a_failed_download_fails_the_build_in_ci_but_only_warns_locally(monkeypatch):
    def offline(url, path, timeout=60):
        raise OSError("offline")

    monkeypatch.setattr(build, "_download", offline)
    assert build.ensure_biome_binary() is None

    monkeypatch.setenv("CI", "true")
    with pytest.raises(OSError):
        build.ensure_biome_binary()


def node_archive():
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:xz") as archive:
        data = b"#!/bin/sh\n"
        info = tarfile.TarInfo(f"node-v{build.NODE_VERSION}-linux-x64/bin/node")
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def test_node_is_extracted_only_from_an_archive_with_the_pinned_checksum(monkeypatch):
    archive = node_archive()
    monkeypatch.setattr(
        build,
        "_download",
        lambda url, path, timeout=60: pathlib.Path(path).write_bytes(archive),
    )

    monkeypatch.setitem(build._NODE_ARCHIVE_HASHES, "linux-x64", "0" * 64)
    assert build.ensure_node_binary() is None

    monkeypatch.setitem(
        build._NODE_ARCHIVE_HASHES, "linux-x64", hashlib.sha256(archive).hexdigest()
    )
    node = build.ensure_node_binary()
    assert os.access(node, os.X_OK)


def test_zap_addons_with_the_wrong_checksum_are_refused(monkeypatch):
    monkeypatch.setattr(
        build, "_download", lambda url, path, timeout=60: open(path, "wb").write(b"x")
    )

    assert build.ensure_zap_addons() is None
