"""Varnostna kopija: shrani prenos, obnovi na novem profilu, napačno in pravo geslo, tuja datoteka."""

import json

import pytest
from app_helpers import db_state, open_app, seed
from playwright.sync_api import expect

PASSWORD = "testno-geslo-za-kopijo"
SECRET_NOTE = "skrivna opomba: poškodba kolena"
CLIENTS = [
    {
        "name": "Ana Novak",
        "notes": [
            {"date": "2026-10-01 09:00", "text": SECRET_NOTE},
            {"date": "2026-10-02 09:00", "text": "# drugi"},
        ],
    },
    {
        "name": "Bor Zajc",
        "notes": [{"date": "2026-10-03 18:30", "text": "borov zapis"}],
    },
]


def save_backup(page, tmp_path):
    page.get_by_role("button", name="Shrani kopijo").click()
    page.locator("#pw-value").fill(PASSWORD)
    with page.expect_download() as download:
        page.locator("#pw-confirm").click()
    path = tmp_path / "kopija.json"
    download.value.save_as(path)
    return download.value.suggested_filename, path


@pytest.fixture
def backup(page, base_url, tmp_path):
    seed(page, base_url, CLIENTS)
    name, path = save_backup(page, tmp_path)
    return page, name, path


def fresh_profile(browser, browser_context_args, base_url, accept=True):
    context = browser.new_context(**browser_context_args)
    page = context.new_page()
    page.on(
        "dialog", lambda d: d.accept() if accept else d.dismiss()
    )  # potrditev zamenjave
    open_app(page, base_url)
    return context, page


def restore(page, path_or_file):
    page.locator("input[type=file]").set_input_files(path_or_file)


def unlock(page, password):
    page.wait_for_selector("#dialog-password[open]")
    page.locator("#pw-value").fill(password)
    page.locator("#pw-confirm").click()


def test_prenesena_datoteka_je_šifrirana_ovojnica_brez_čistopisa(backup):
    _page, name, path = backup
    text = path.read_text()
    envelope = json.loads(text)
    assert name.startswith("libreptnotes-") and name.endswith(".json")
    assert envelope["formatVersion"] == 6
    assert envelope["container"] == "aes-gcm"
    assert envelope["kdf"] == {
        "name": "PBKDF2",
        "hash": "SHA-256",
        "iterations": 600000,
    }
    for secret in (SECRET_NOTE, "Ana Novak", "Bor Zajc", PASSWORD):
        assert secret not in text


def test_shranjena_kopija_se_vrne_na_isti_napravi_brez_vprašanja_za_geslo(backup):
    page, _name, path = backup
    page.on("dialog", lambda d: d.accept())
    restore(page, path)
    expect(page.locator("#view .backup .status")).to_have_text(
        "Obnovljeno. Stranke: 2, zapisi: 3."
    )
    assert page.locator("#dialog-password[open]").count() == 0


def test_nov_profil_zavrne_napačno_geslo_in_sprejme_pravo(
    backup, browser, browser_context_args, base_url
):
    _page, _name, path = backup
    context, fresh = fresh_profile(browser, browser_context_args, base_url)
    restore(fresh, path)
    unlock(fresh, "napačno-geslo")
    expect(fresh.locator("#view .backup .status")).to_have_text(
        "Napačno geslo ali spremenjena datoteka."
    )
    assert db_state(fresh)["clients"] == []

    restore(fresh, path)
    unlock(fresh, PASSWORD)
    expect(fresh.locator("#view .backup .status")).to_have_text(
        "Obnovljeno. Stranke: 2, zapisi: 3."
    )
    assert fresh.locator(".client-name").all_inner_texts() == ["Ana Novak", "Bor Zajc"]
    notes = sorted(n["text"] for n in db_state(fresh)["notes"])
    assert notes == sorted([SECRET_NOTE, "# drugi", "borov zapis"])
    context.close()


def test_obnovitev_zamenja_vse_na_napravi(
    backup, browser, browser_context_args, base_url
):
    _page, _name, path = backup
    context, fresh = fresh_profile(browser, browser_context_args, base_url)
    seed(fresh, base_url, [{"name": "Stara stranka", "notes": []}])
    restore(fresh, path)
    unlock(fresh, PASSWORD)
    expect(fresh.locator("#view .backup .status")).to_contain_text("Obnovljeno")
    assert "Stara stranka" not in fresh.locator(".client-name").all_inner_texts()
    context.close()


def test_preklic_potrditve_ne_spremeni_podatkov(
    backup, browser, browser_context_args, base_url
):
    _page, _name, path = backup
    context, fresh = fresh_profile(
        browser, browser_context_args, base_url, accept=False
    )
    seed(fresh, base_url, [{"name": "Stara stranka", "notes": []}])
    restore(fresh, path)
    unlock(fresh, PASSWORD)
    fresh.wait_for_selector("#dialog-password", state="hidden")
    expect(fresh.locator("#view .backup .status")).to_have_text("")
    assert fresh.locator(".client-name").all_inner_texts() == ["Stara stranka"]
    context.close()


FOREIGN_FILES = [
    b"to ni json",
    b'{"clients": [], "notes": []}',
    b'{"container": "aes-gcm", "ciphertext": "x", "formatVersion": 4}',
]


@pytest.mark.parametrize("content", FOREIGN_FILES)
def test_tuja_datoteka_je_zavrnjena(page, base_url, content):
    open_app(page, base_url)
    page.on("dialog", lambda d: d.accept())
    restore(
        page, {"name": "tuja.json", "mimeType": "application/json", "buffer": content}
    )
    expect(page.locator("#view .backup .status")).to_have_text(
        "Datoteka ni kopija LibrePTNotes."
    )
    assert db_state(page)["clients"] == []


FOREIGN_JS = """
async ([password, app]) => {
  const { randomSalt, deriveAesKey } = await import("./data/passphraseKey.js");
  const { encryptBackup } = await import("./data/backupEncryption.js");
  const salt = randomSalt();
  const key = await deriveAesKey(password, salt);
  const payload = { app, schemaVersion: 1, clients: [], notes: [] };
  return JSON.stringify(await encryptBackup(payload, { key, salt, formatVersion: 6 }));
}
"""


def test_pravilno_šifrirana_datoteka_druge_aplikacije_je_zavrnjena(page, base_url):
    open_app(page, base_url)
    page.on("dialog", lambda d: d.accept())
    foreign = page.evaluate(FOREIGN_JS, [PASSWORD, "librept"])
    restore(
        page,
        {
            "name": "librept.json",
            "mimeType": "application/json",
            "buffer": foreign.encode(),
        },
    )
    unlock(page, PASSWORD)
    expect(page.locator("#view .backup .status")).to_have_text(
        "Datoteka ni kopija LibrePTNotes."
    )


def test_spremenjena_datoteka_je_zavrnjena(
    backup, browser, browser_context_args, base_url
):
    _page, _name, path = backup
    envelope = json.loads(path.read_text())
    cipher = envelope["ciphertext"]
    envelope["ciphertext"] = ("A" if cipher[0] != "A" else "B") + cipher[1:]
    context, fresh = fresh_profile(browser, browser_context_args, base_url)
    restore(
        fresh,
        {
            "name": "spremenjena.json",
            "mimeType": "application/json",
            "buffer": json.dumps(envelope).encode(),
        },
    )
    unlock(fresh, PASSWORD)
    expect(fresh.locator("#view .backup .status")).to_have_text(
        "Napačno geslo ali spremenjena datoteka."
    )
    assert db_state(fresh)["clients"] == []
    context.close()


def test_zgresen_vnos_pri_obnovi_ne_prepise_gesla_naprave(backup, tmp_path, base_url):
    # Najdba raziskovalnega testiranja: z obkljukanim »Zapomni si« je napačen vnos tiho zamenjal
    # geslo, s katerim se pišejo kopije; datoteke nato ni bilo več mogoče odpreti z gesli trenerja.
    page, _name, path = backup
    other = tmp_path / "tuja.json"
    context, foreign = fresh_profile(page.context.browser, {}, base_url)
    seed(foreign, base_url, CLIENTS)
    foreign.get_by_role("button", name="Shrani kopijo").click()
    foreign.locator("#pw-value").fill("tuje-geslo-z-druge-naprave")
    with foreign.expect_download() as download:
        foreign.locator("#pw-confirm").click()
    download.value.save_as(other)
    context.close()

    restore(page, other)
    page.wait_for_selector("#dialog-password[open]")
    expect(page.locator("#pw-remember-row")).to_be_hidden()  # naprava že ima geslo
    page.locator("#pw-value").fill("zgresen-vnos")
    page.locator("#pw-confirm").click()
    expect(page.locator(".backup .status")).to_contain_text("Napačno geslo")
    page.reload()
    name, again = save_backup_with_stored_password(page, tmp_path)
    context2, third = fresh_profile(page.context.browser, {}, base_url)
    restore(third, again)
    unlock(third, PASSWORD)
    expect(third.locator(".backup .status")).to_contain_text("Obnovljeno")
    context2.close()


def save_backup_with_stored_password(page, tmp_path):
    """Shrani kopijo z geslom, ki ga naprava že ima (brez vprašanja)."""
    with page.expect_download() as download:
        page.get_by_role("button", name="Shrani kopijo").click()
    path = tmp_path / "ponovna.json"
    download.value.save_as(path)
    return download.value.suggested_filename, path


def test_nova_naprava_po_zgresenem_vnosu_ne_dobi_gesla(backup, base_url):
    _page, _name, path = backup
    context, fresh = fresh_profile(backup[0].context.browser, {}, base_url)
    restore(fresh, path)
    fresh.wait_for_selector("#dialog-password[open]")
    expect(
        fresh.locator("#pw-remember-row")
    ).to_be_visible()  # prazna naprava: ponudba velja
    fresh.locator("#pw-value").fill("napacno")
    fresh.locator("#pw-confirm").click()
    expect(fresh.locator(".backup .status")).to_contain_text("Napačno geslo")
    fresh.reload()
    expect(fresh.locator(".backup")).to_contain_text("ni nastavljeno")
    context.close()
