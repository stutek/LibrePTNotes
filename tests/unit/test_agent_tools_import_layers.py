"""import_layers: sloji domain < data < ui < app, samostojni gesture/i18n/sw, čist domain."""

from agent_tools import import_layers


def found(tmp_path, files):
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return [(rel, message) for rel, _n, message in import_layers.find_all(tmp_path)]


BASE = {
    "src/domain/notes.js": "export const n = 1;\n",
    "src/data/store.js": 'import { n } from "../domain/notes.js";\n',
    "src/ui/view.js": 'import { n } from "../domain/notes.js";\nimport "../data/store.js";\n',
    "src/gesture/peek.js": "export const p = 1;\n",
    "src/i18n.js": "export const t = (k) => k;\n",
    "src/sw.js": "self.addEventListener('install', () => {});\n",
}


def test_downward_imports_pass(tmp_path):
    files = {
        **BASE,
        "src/app.js": 'import "./ui/view.js";\nimport "./i18n.js";\nimport "./data/store.js";\n',
    }
    assert found(tmp_path, files) == []


def test_data_importing_ui_and_domain_importing_data_are_reported(tmp_path):
    files = {
        **BASE,
        "src/data/store.js": 'import "../ui/view.js";\n',
        "src/domain/notes.js": 'import "../data/store.js";\n',
    }
    messages = [m for _rel, m in found(tmp_path, files)]
    assert any(m.startswith("data uvaža ui") for m in messages)
    assert any(m.startswith("domain uvaža data") for m in messages)


def test_ui_must_not_import_the_dictionary_directly(tmp_path):
    files = {**BASE, "src/ui/view.js": 'import { t } from "../i18n.js";\n'}
    assert any(m.startswith("ui uvaža i18n") for _rel, m in found(tmp_path, files))


def test_gesture_is_standalone_but_ui_may_use_it(tmp_path):
    files = {
        **BASE,
        "src/gesture/peek.js": 'import "../domain/notes.js";\n',
        "src/ui/view.js": 'import "../gesture/peek.js";\n',
    }
    messages = [m for rel, m in found(tmp_path, files)]
    assert any(m.startswith("gesture uvaža domain") for m in messages)
    assert not any(m.startswith("ui uvaža gesture") for m in messages)


def test_domain_and_data_cannot_use_the_gesture_copy(tmp_path):
    files = {**BASE, "src/domain/notes.js": 'import "../gesture/peek.js";\n'}
    assert any(
        m.startswith("domain uvaža gesture") for _rel, m in found(tmp_path, files)
    )


def test_service_worker_and_dictionary_import_nothing(tmp_path):
    files = {
        **BASE,
        "src/sw.js": 'import "./i18n.js";\nimportScripts("x.js");\n',
        "src/i18n.js": 'import "./domain/notes.js";\n',
    }
    messages = [m for _rel, m in found(tmp_path, files)]
    assert any(m.startswith("sw uvaža i18n") for m in messages)
    assert any("importScripts" in m for m in messages)
    assert any(m.startswith("i18n uvaža domain") for m in messages)


def test_domain_must_be_pure_but_a_comment_may_mention_the_dom(tmp_path):
    pure = {
        **BASE,
        "src/domain/notes.js": "// ne rabi document ali window\nexport const n = 1;\n",
    }
    impure = {**BASE, "src/domain/notes.js": "export const n = document.title;\n"}
    assert found(tmp_path / "a", pure) == []
    assert any(
        "čist" in m and "document" in m for _rel, m in found(tmp_path / "b", impure)
    )


def test_import_to_a_missing_file_and_bare_specifiers_are_reported(tmp_path):
    files = {
        **BASE,
        "src/ui/view.js": 'import "../data/gone.js";\nimport x from "lodash";\n',
    }
    messages = [m for _rel, m in found(tmp_path, files)]
    assert any("gone.js" in m and "ne kaže na nobeno datoteko" in m for m in messages)
    assert any("lodash" in m for m in messages)


def test_multiline_and_reexport_imports_are_followed(tmp_path):
    files = {
        **BASE,
        "src/domain/notes.js": 'import {\n  a,\n  b,\n} from "../ui/view.js";\nexport { c } from "../data/store.js";\n',
    }
    assert (
        len([m for _rel, m in found(tmp_path, files) if m.startswith("domain uvaža")])
        == 2
    )


def test_main_exit_codes(tmp_path):
    (tmp_path / "ok" / "src" / "domain").mkdir(parents=True)
    (tmp_path / "ok" / "src" / "domain" / "a.js").write_text(
        "export const a = 1;\n", encoding="utf-8"
    )
    (tmp_path / "bad" / "src" / "domain").mkdir(parents=True)
    (tmp_path / "bad" / "src" / "domain" / "a.js").write_text(
        'import "./nope.js";\n', encoding="utf-8"
    )
    assert import_layers.main(tmp_path / "ok") == 0
    assert import_layers.main(tmp_path / "bad") == 1
