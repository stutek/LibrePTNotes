"""Namizni brskalnik (zgled LibrePT): urejevalnik mora biti viden in pripravljen za pisanje."""

import pytest
from app_helpers import seed
from playwright.sync_api import expect

CLIENT = [{"name": "Ana", "notes": [{"date": "2026-10-01 09:00", "text": ""}]}]
TABS = {"open": ["Ana"], "active": "Ana"}


@pytest.fixture
def desktop(browser, base_url):
    context = browser.new_context(
        viewport={"width": 1280, "height": 800}, color_scheme="light"
    )
    page = context.new_page()
    seed(page, base_url, CLIENT, tabs=TABS)
    page.wait_for_selector(".plan-peek-blanket .md-input")
    yield page
    context.close()


def test_prazen_zapis_pove_kam_pisati_in_je_fokusiran_z_mišjo(desktop):
    editor = desktop.locator(".plan-peek-blanket .md-input")
    assert editor.get_attribute("placeholder")
    expect(editor).to_be_focused()


def test_urejevalnik_je_na_strani_razločen_od_ozadja(desktop):
    # Najdba lastnika: »sploh ne vidim urejevalnika« (bela kartica na skoraj beli strani brez roba).
    body = desktop.locator(".plan-peek-blanket .note-body")
    border = body.evaluate("e => getComputedStyle(e).borderTopColor")
    page_bg = desktop.evaluate(
        "() => getComputedStyle(document.documentElement).backgroundColor"
    )
    assert border != page_bg
    box = body.bounding_box()
    assert box["height"] >= 300


def test_ozadje_zapisa_je_enotno_brez_stopničastega_roba(desktop):
    # Zapis (blanket) je neprosoren in se premika; preliv strani bi za njim naredil viden pravokotnik.
    image = desktop.evaluate("() => getComputedStyle(document.body).backgroundImage")
    assert image == "none"
    desktop.locator(".tab-name", has_text="Stranke").click()
    desktop.wait_for_selector(".client-list, .empty")
    assert (
        desktop.evaluate("() => getComputedStyle(document.body).backgroundImage")
        != "none"
    )


def test_na_telefonu_zapis_ne_odpre_tipkovnice_sam(page, base_url):
    seed(page, base_url, CLIENT, tabs=TABS)
    page.wait_for_selector(".plan-peek-blanket .md-input")
    expect(page.locator(".plan-peek-blanket .md-input")).not_to_be_focused()
