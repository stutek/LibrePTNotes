"""Dialog z geslom kopije: prikaz, generiranje, prazno geslo, zapiranje."""

import pytest
from playwright.sync_api import expect
from app_helpers import open_app


@pytest.fixture
def dialog_page(page, base_url):
    open_app(page, base_url)
    page.get_by_role("button", name="Shrani kopijo").click()
    page.wait_for_selector("#dialog-password[open]")
    return page


def test_dialog_ponudi_geslo_iz_šestih_besed_v_celoti(dialog_page):
    value = dialog_page.locator("#pw-value").input_value()
    assert len(value.split("-")) == 7  # šest besed in naključen niz
    area = dialog_page.locator("#pw-value")
    assert area.evaluate("e => e.scrollHeight <= e.clientHeight")  # geslo ni odrezano
    assert dialog_page.locator("#pw-warning").is_visible()


def test_dialog_je_znotraj_zaslona_telefona(dialog_page):
    box = dialog_page.locator("#dialog-password").bounding_box()
    assert box["x"] >= 0
    assert box["x"] + box["width"] <= 390
    assert box["y"] + box["height"] <= 780


def test_nov_predlog_zamenja_geslo(dialog_page):
    before = dialog_page.locator("#pw-value").input_value()
    dialog_page.locator("#pw-generate").click()
    assert dialog_page.locator("#pw-value").input_value() != before


def test_prazno_geslo_ne_zapre_dialoga_in_pove_zakaj(dialog_page):
    dialog_page.locator("#pw-value").fill("   ")
    dialog_page.locator("#pw-confirm").click()
    assert dialog_page.locator("#pw-status").inner_text() == "Vpiši geslo."
    assert dialog_page.locator("#dialog-password[open]").count() == 1


def test_zapiranje_vrne_na_seznam_brez_kopije(dialog_page):
    dialog_page.locator("#pw-cancel").click()
    assert dialog_page.locator("#dialog-password[open]").count() == 0
    expect(dialog_page.locator("#view .backup .status")).to_have_text(
        "Brez gesla kopije ni mogoče shraniti."
    )


def test_escape_zapre_dialog_kot_zapiranje(dialog_page):
    dialog_page.keyboard.press("Escape")
    dialog_page.wait_for_selector("#dialog-password", state="hidden")
    expect(dialog_page.locator("#view .backup .status")).to_have_text(
        "Brez gesla kopije ni mogoče shraniti."
    )


def test_ciljne_površine_gumbov_so_dovolj_velike(dialog_page):
    for button in dialog_page.locator("#dialog-password button").all():
        box = button.bounding_box()
        assert box["height"] >= 44, button.inner_text()


def test_prekratko_lastno_geslo_se_zavrne(dialog_page):
    dialog_page.locator("#pw-value").fill("abc")
    dialog_page.locator("#pw-confirm").click()
    expect(dialog_page.locator("#pw-status")).to_contain_text("vsaj 8")
    expect(dialog_page.locator("#dialog-password")).to_be_visible()


def test_kratko_lastno_geslo_opozori_in_se_sprejme_ob_ponovnem_potrdilu(dialog_page):
    dialog_page.locator("#pw-value").fill("kratko123")
    dialog_page.locator("#pw-confirm").click()
    expect(dialog_page.locator("#pw-status")).to_contain_text("kratko")
    expect(dialog_page.locator("#dialog-password")).to_be_visible()
    with dialog_page.expect_download():
        dialog_page.locator("#pw-confirm").click()
    expect(dialog_page.locator("#dialog-password")).to_be_hidden()


def test_sprememba_besedila_po_opozorilu_opozori_znova(dialog_page):
    dialog_page.locator("#pw-value").fill("kratko123")
    dialog_page.locator("#pw-confirm").click()
    dialog_page.locator("#pw-value").fill("drugo1234")
    dialog_page.locator("#pw-confirm").click()
    expect(dialog_page.locator("#dialog-password")).to_be_visible()
