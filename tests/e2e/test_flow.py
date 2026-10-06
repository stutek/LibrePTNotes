"""Celotni tokovi: stranke, zavihek, zapisi, obstojnost po ponovnem nalaganju."""

import re

from app_helpers import (
    active_tab,
    db_state,
    notes_of,
    open_app,
    open_client,
    wait_for_saved,
    wait_for_service_worker,
)
from playwright.sync_api import expect

ISO = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")


def add_client(page, name):
    """Doda stranko na seznamu (ne prve: ta odpre svoj zapis, glej add_first_client)."""
    page.locator("#client-name").fill(name)
    page.locator(".add-client button[type=submit]").click()
    expect(page.locator(".client-name", has_text=name)).to_be_visible()


def add_first_client(page, name):
    """Prva stranka aplikacijo sama odpre v njenem zavihku, v pogledu zapisa."""
    page.locator("#client-name").fill(name)
    page.locator(".add-client button[type=submit]").click()
    expect(page.locator(".plan-peek-blanket .md-input")).to_be_focused()
    assert active_tab(page) == name


def back_to_list(page):
    page.locator(".tab-name", has_text="Stranke").click()
    expect(page.locator("#view .client-list")).to_be_visible()


def test_stranke_zavihek_zapisi(page, base_url):
    open_app(page, base_url)
    wait_for_service_worker(page)
    expect(page.locator("#view .welcome")).to_contain_text("Beležke za tvoje stranke")
    assert page.locator("#view .client-row").count() == 0
    add_first_client(page, "Žan Kralj")
    back_to_list(page)
    add_client(page, "Ana Novak")
    # Slovenska abeceda: Ana pred Žanom.
    assert page.locator(".client-name").all_inner_texts() == ["Ana Novak", "Žan Kralj"]

    open_client(page, "Ana Novak")
    expect(page.locator("#view .note-empty p")).to_have_text(
        "Ta stranka še nima zapisov."
    )
    assert active_tab(page) == "Ana Novak"

    page.get_by_role("button", name="Nov zapis").click()
    editor = page.locator(".plan-peek-blanket .md-input")
    expect(editor).to_be_visible()
    editor.fill("# Prvi zapis\nstrah pred počepom")
    wait_for_saved(page, "Ana Novak", ["# Prvi zapis\nstrah pred počepom"])
    [note] = notes_of(page, "Ana Novak")
    assert ISO.match(note["date"])
    expect(page.locator(".note-count")).to_have_text("1 / 1")


def test_ime_stranke_ne_sme_biti_prazno(page, base_url):
    open_app(page, base_url)
    page.locator("#client-name").fill("   ")
    page.locator(".add-client button[type=submit]").click()
    expect(page.locator(".form-error")).to_be_visible()
    expect(page.locator("#view .welcome")).to_be_visible()
    assert db_state(page)["clients"] == []


def test_stanje_ostane_po_ponovnem_nalaganju(page, base_url):
    open_app(page, base_url)
    add_first_client(page, "Ana")
    back_to_list(page)
    add_client(page, "Bor")
    for name in ("Ana", "Bor"):
        back_to_list(page)
        open_client(page, name)
        page.wait_for_selector(".note-empty, .plan-peek-blanket .md-input")
        if page.locator(".note-empty").count():  # Ana ima prvi zapis že od prve stranke
            page.get_by_role("button", name="Nov zapis").click()
        page.locator(".plan-peek-blanket .md-input").fill(f"zapis {name}")
        wait_for_saved(page, name, [f"zapis {name}"])
    page.locator(".tab-name", has_text="Ana").click()
    expect(page.locator(".plan-peek-blanket .md-input")).to_have_value("zapis Ana")

    page.reload()
    expect(page.locator(".plan-peek-blanket .md-input")).to_have_value("zapis Ana")
    assert page.locator(".tab-name").all_inner_texts() == ["Stranke", "Ana", "Bor"]
    assert active_tab(page) == "Ana"
    page.get_by_role("button", name="Zapri zavihek: Ana").click()
    expect(page.locator(".tab-name")).to_have_text(["Stranke", "Bor"])
    page.reload()
    assert page.locator(".tab-name").all_inner_texts() == ["Stranke", "Bor"]
    assert active_tab(page) == "Stranke"


def test_besedilo_se_shrani_tudi_ob_hitrem_zapiranju_strani(page, base_url):
    open_app(page, base_url)
    add_first_client(page, "Ana")
    page.locator(".plan-peek-blanket .md-input").fill("hitro")
    page.locator(
        ".tab-name", has_text="Stranke"
    ).click()  # izplakne neshranjeno besedilo
    wait_for_saved(page, "Ana", ["hitro"])


def test_baza_ime_in_predpomnilnik_ne_trčita_z_librept(page, base_url):
    open_app(page, base_url)
    wait_for_service_worker(page)
    names = page.evaluate(
        "async () => (await indexedDB.databases()).map((d) => d.name)"
    )
    assert names == ["libreptnotes"]
    caches = page.evaluate("() => caches.keys()")
    assert caches
    assert all(name.startswith("libreptnotes-") for name in caches)
    assert not any(re.match(r"^librept-", name) for name in caches)
    assert page.evaluate("() => localStorage.length") == 0
