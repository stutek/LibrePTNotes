"""Urejanje datuma zapisa (specifikacija: datum je urejljiv): besedilno polje, veljaven vnos, `created` ostane."""

import pytest
from app_helpers import Touch, db_state, seed, wait_for_saved
from playwright.sync_api import expect

NOTES = [
    {"date": "2026-10-01 09:00", "text": "prvi"},
    {"date": "2026-10-02 09:00", "text": "drugi"},
    {"date": "2026-10-03 09:00", "text": "tretji"},
]


@pytest.fixture
def note_page(page, base_url):
    seed(
        page,
        base_url,
        [{"name": "Ana", "notes": NOTES, "current": 1}],
        tabs={"open": ["Ana"], "active": "Ana"},
    )
    page.wait_for_selector(".note-date")
    return page


def stored(page, text):
    return next(n for n in db_state(page)["notes"] if n["text"] == text)


def test_veljaven_datum_se_shrani_in_zapis_se_preuredi(note_page):
    created_before = stored(note_page, "drugi")["created"]
    note_page.locator(".note-date").click()
    field = note_page.locator(".note-date-input")
    expect(field).to_have_value("2026-10-02 09:00")
    field.fill("2026-10-04 12:30")
    field.press("Enter")
    expect(note_page.locator(".note-date")).to_have_text("2026-10-04 12:30")
    expect(note_page.locator(".note-count")).to_have_text("3 / 3")
    saved = stored(note_page, "drugi")
    assert saved["date"] == "2026-10-04 12:30"
    assert saved["created"] == created_before
    assert saved["text"] == "drugi"
    # Zapis ostane trenutni: po ponovnem nalaganju je še vedno odprt.
    note_page.reload()
    expect(note_page.locator(".note-date")).to_have_text("2026-10-04 12:30")


def test_neveljaven_datum_se_ne_shrani_in_pove_zakaj(note_page):
    note_page.locator(".note-date").click()
    field = note_page.locator(".note-date-input")
    field.fill("2026-10-02 24:00")
    field.press("Enter")
    expect(field).to_have_attribute("aria-invalid", "true")
    expect(note_page.locator(".note-date-error")).to_be_visible()
    assert stored(note_page, "drugi")["date"] == "2026-10-02 09:00"
    field.fill("2026-10-02 18:45")
    field.press("Enter")
    expect(note_page.locator(".note-date")).to_have_text("2026-10-02 18:45")
    assert stored(note_page, "drugi")["date"] == "2026-10-02 18:45"


def test_escape_zavrže_urejanje(note_page):
    note_page.locator(".note-date").click()
    field = note_page.locator(".note-date-input")
    field.fill("1999-01-01 00:00")
    field.press("Escape")
    expect(note_page.locator(".note-date")).to_have_text("2026-10-02 09:00")
    assert stored(note_page, "drugi")["date"] == "2026-10-02 09:00"


def test_polje_je_besedilno_in_24_urno_ne_glede_na_telefon(note_page):
    note_page.locator(".note-date").click()
    field = note_page.locator(".note-date-input")
    assert field.get_attribute("type") == "text"
    assert field.get_attribute("inputmode") == "numeric"
    box = field.bounding_box()
    assert box["height"] >= 44


def gesture_to(page, dx):
    """Kretnja L: zadrži, povleci vstran (dx), povleci navzgor."""
    touch = Touch(page)
    touch.hold(195, 400)
    touch.pull(dx)
    touch.raise_(90)
    touch.up()


def test_kretnja_z_odprtim_poljem_datuma_ustvari_zapis_in_ga_shrani(page, base_url):
    # Najdba raziskovalnega testiranja: nov zapis je izginil in v konzoli je bila napaka, ker je
    # polje datuma ostalo odprto, ko ga je kretnja zamenjala.
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    seed(
        page,
        base_url,
        [{"name": "Ana", "notes": NOTES, "current": 2}],
        tabs={"open": ["Ana"], "active": "Ana"},
    )
    page.wait_for_selector(".note-date")
    page.locator(".note-date").click()
    expect(page.locator(".note-date-input")).to_be_visible()
    gesture_to(page, -150)
    expect(page.locator(".note-count")).to_have_text("4 / 4")
    page.locator(".plan-peek-blanket .md-input").fill("nov zapis po kretnji")
    wait_for_saved(page, "Ana", ["prvi", "drugi", "tretji", "nov zapis po kretnji"])
    page.reload()
    expect(page.locator(".note-count")).to_have_text("4 / 4")
    expect(page.locator(".plan-peek-blanket .md-input")).to_have_value(
        "nov zapis po kretnji"
    )
    assert errors == []


def test_kretnja_na_sosednji_zapis_zapre_polje_datuma(note_page):
    errors = []
    note_page.on("pageerror", lambda e: errors.append(str(e)))
    note_page.locator(".note-date").click()
    gesture_to(note_page, 150)
    expect(note_page.locator(".note-date")).to_have_text("2026-10-01 09:00")
    expect(note_page.locator(".note-date-input")).to_have_count(0)
    assert errors == []
