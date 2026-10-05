"""run_build: what ends up in dist/ is exactly what the service worker and Pages will serve."""

import hashlib
import json
import re

import pytest

from build import run_build


@pytest.fixture
def tree(tmp_path):
    src = tmp_path / "src"
    (src / "data").mkdir(parents=True)
    (src / "index.html").write_text(
        "<!doctype html><title>t</title>\n", encoding="utf-8"
    )
    (src / "data" / "store.js").write_text("export const a = 1;\n", encoding="utf-8")
    (src / "sw.js").write_text("// sw\n", encoding="utf-8")
    return tmp_path


def build(tree):
    run_build(dist_dir=str(tree / "dist"), src_dir=str(tree / "src"))
    return tree / "dist"


def test_dist_is_a_copy_of_src_plus_the_publishing_files(tree):
    dist = build(tree)

    for name in ("index.html", "data/store.js", "sw.js"):
        assert (dist / name).read_bytes() == (tree / "src" / name).read_bytes()
    assert (dist / ".nojekyll").exists()
    assert (dist / "version.js").exists()
    assert (dist / "integrity.json").exists()
    # Nothing a router-based site would need: the app has no router.
    assert not (dist / "404.html").exists()


def test_integrity_catalog_hashes_the_exact_bytes_that_ship(tree):
    dist = build(tree)

    catalog = json.loads((dist / "integrity.json").read_text(encoding="utf-8"))

    assert catalog["algorithm"] == "SHA-256"
    shipped = {
        str(path.relative_to(dist)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in dist.rglob("*")
        if path.is_file() and path.name != "integrity.json"
    }
    assert catalog["files"] == shipped
    assert "integrity.json" not in catalog["files"]
    # The version stamp is written before the catalog, so it is covered too.
    assert "version.js" in catalog["files"]


def test_version_stamp_carries_commit_and_build_time(tree):
    dist = build(tree)

    stamp = (dist / "version.js").read_text(encoding="utf-8")

    assert re.fullmatch(
        r'export const BUILD_INFO = \{ commit: "([0-9a-f]+|local)", '
        r'builtAt: "\d{4}-\d\d-\d\dT\d\d:\d\dZ" \};\n',
        stamp,
    )


def test_a_rebuild_drops_files_that_left_src(tree):
    dist = build(tree)
    (tree / "src" / "sw.js").unlink()

    dist = build(tree)

    assert not (dist / "sw.js").exists()
    assert (
        "sw.js"
        not in json.loads((dist / "integrity.json").read_text(encoding="utf-8"))[
            "files"
        ]
    )


def test_building_without_a_source_tree_fails(tmp_path):
    with pytest.raises(SystemExit) as stop:
        run_build(dist_dir=str(tmp_path / "dist"), src_dir=str(tmp_path / "missing"))

    assert stop.value.code == 1


def test_build_names_a_new_cache_after_every_commit(tmp_path, monkeypatch):
    # The service worker only updates when its bytes change; the commit count is what changes.
    import build

    (tmp_path / "sw.js").write_text("const CACHE_VERSION = 1;\n")
    monkeypatch.setattr(build.subprocess, "check_output", lambda *a, **k: b"42\n")
    build.stamp_cache_version(str(tmp_path))
    assert (tmp_path / "sw.js").read_text() == "const CACHE_VERSION = 42;\n"
