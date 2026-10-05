"""catalog_coverage: vsak modul v src/ je v katalogu in vsak naštet modul obstaja."""

from agent_tools import catalog_coverage as cc

FRONT = "---\ntype: catalog\ntitle: K\ndescription: D\ntags: [a]\n---\n\n"


def project(tmp_path, modules, catalog_lines):
    for rel in modules:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs" / "modules.md").write_text(
        FRONT + "\n".join(catalog_lines) + "\n", encoding="utf-8"
    )
    return tmp_path


def entry(path, text="opis"):
    return f"* [{path}](../{path}) — {text}"


def test_complete_catalog_passes_and_icons_or_manifest_are_not_modules(tmp_path):
    root = project(
        tmp_path,
        [
            "src/app.js",
            "src/app.css",
            "src/index.html",
            "src/icons/i.png",
            "src/manifest.webmanifest",
        ],
        [entry("src/app.js"), entry("src/app.css"), entry("src/index.html")],
    )
    assert cc.find_all(root) == ([], [], [])


def test_uncatalogued_module_is_reported(tmp_path):
    root = project(tmp_path, ["src/app.js", "src/ui/new.js"], [entry("src/app.js")])
    assert cc.find_all(root) == (["src/ui/new.js"], [], [])


def test_stale_entry_is_reported_but_non_module_links_are_ignored(tmp_path):
    root = project(
        tmp_path,
        ["src/app.js"],
        [entry("src/app.js"), entry("src/gone.js"), entry("src/icons/x.png")],
    )
    assert cc.find_all(root) == ([], ["src/gone.js"], [])


def test_entry_without_description_is_reported(tmp_path):
    root = project(tmp_path, ["src/app.js"], ["* [src/app.js](../src/app.js)"])
    assert cc.find_all(root) == ([], [], ["src/app.js"])


def test_main_exit_codes_including_a_missing_catalog(tmp_path):
    ok = project(tmp_path / "ok", ["src/app.js"], [entry("src/app.js")])
    bad = project(tmp_path / "bad", ["src/app.js"], [])
    (tmp_path / "none").mkdir()
    assert cc.main(ok) == 0
    assert cc.main(bad) == 1
    assert cc.main(tmp_path / "none") == 1
