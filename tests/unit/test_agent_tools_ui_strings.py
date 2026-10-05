"""ui_strings: besedila mimo t(), neznani in mrtvi ključi slovarja."""

from agent_tools import ui_strings

I18N = 'const STRINGS = {\n  save: "Shrani",\n  cancel: "Prekliči",\n};\nexport function t(key) { return STRINGS[key] ?? key; }\n'


def project(tmp_path, files):
    files = {"src/i18n.js": I18N, **files}
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def messages(root):
    return [f"{rel}:{n} {message}" for rel, n, message in ui_strings.find_all(root)]


def test_text_through_t_is_clean(tmp_path):
    ui = 'el("button", { text: t("save"), attrs: { "aria-label": t("cancel") } });\n'
    assert messages(project(tmp_path, {"src/ui/a.js": ui})) == []


def test_literal_text_in_code_is_reported_for_each_user_visible_slot(tmp_path):
    ui = (
        'el("b", { text: "Dodaj" });\n'
        'x.textContent = "Zapri";\n'
        'el("i", { attrs: { placeholder: "Ime", "aria-label": "Zapri zavihek" } });\n'
        'if (confirm("Res izbrišem?")) {}\n'
        "const row = `<span>Prazen zapis</span>`;\n"
        + 'const s = t("save") + t("cancel");\n'
    )
    found = messages(project(tmp_path, {"src/ui/a.js": ui}))
    assert len([m for m in found if "mimo t()" in m]) == 6


def test_symbols_and_interpolation_glue_are_not_text(tmp_path):
    ui = (
        'el("b", { text: "✕" });\n'
        'el("b", { text: `${t("save")}: ${name}` });\n'
        "if (a.created > b.created && c < d) {}\n"
        'const s = t("save") + t("cancel");\n'
    )
    assert messages(project(tmp_path, {"src/ui/a.js": ui})) == []


def test_static_text_and_attributes_in_html_are_reported_but_title_is_not(tmp_path):
    html = '<title>LibrePTNotes</title>\n<h2>Geslo</h2>\n<button aria-label="Zapri"></button>\n<h2 id="x"></h2>\n'
    found = messages(
        project(
            tmp_path, {"src/index.html": html, "src/a.js": 't("save"); t("cancel");\n'}
        )
    )
    assert len([m for m in found if "index.html" in m]) == 2


def test_unknown_key_and_unused_key_are_reported(tmp_path):
    found = messages(project(tmp_path, {"src/ui/a.js": 't("save"); t("missing");\n'}))
    assert any("missing" in m and "STRINGS" in m for m in found)
    assert any("cancel" in m and "ne bere nihče" in m for m in found)


def test_dynamic_keys_disable_the_unused_key_report(tmp_path):
    found = messages(
        project(tmp_path, {"src/ui/a.js": 't(`k${n}`); t(name); t("save");\n'})
    )
    assert not any("ne bere nihče" in m for m in found)


def test_dictionary_and_service_worker_are_not_scanned_for_literals(tmp_path):
    root = project(
        tmp_path,
        {
            "src/sw.js": 'const label = { text: "Besedilo" };\n',
            "src/ui/a.js": 't("save"); t("cancel");\n',
        },
    )
    assert messages(root) == []


def test_main_exit_codes(tmp_path):
    ok = project(tmp_path / "ok", {"src/ui/a.js": 't("save"); t("cancel");\n'})
    bad = project(
        tmp_path / "bad",
        {"src/ui/a.js": 'x.title = "Naslov"; t("save"); t("cancel");\n'},
    )
    assert ui_strings.main(ok) == 0
    assert ui_strings.main(bad) == 1
