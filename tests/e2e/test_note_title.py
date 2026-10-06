"""Naslov zapisa: shrani se, preživi ponovni zagon in označi zapis v spodnji plasti kretnje."""

import re

from app_helpers import Touch, db_state, seed
from playwright.sync_api import expect

NOTES = [
    {"date": "2026-10-01 09:00", "text": "prvi"},
    {"date": "2026-10-02 09:00", "text": "# drugi\nvrstica"},
]


def start(page, base_url):
    seed(
        page,
        base_url,
        [{"name": "Ana", "notes": NOTES, "current": 0}],
        tabs={"open": ["Ana"], "active": "Ana"},
    )
    expect(page.locator(".note-title")).to_have_attribute(
        "placeholder", "Naslov (neobvezno)"
    )


def test_naslov_se_shrani_in_preživi_ponovni_zagon(page, base_url):
    start(page, base_url)
    page.locator(".note-title").fill("Počepi in poškodba")
    page.wait_for_function(
        """async () => {
          const { openDb, idbBackend } = await import("./data/idbBackend.js");
          const db = await openDb();
          const notes = await idbBackend(db).getAll("notes");
          db.close();
          return notes.some((n) => n.title === "Počepi in poškodba");
        }"""
    )
    saved = next(n for n in db_state(page)["notes"] if n["text"] == "prvi")
    assert saved["title"] == "Počepi in poškodba" and saved["text"] == "prvi"
    page.reload()
    expect(page.locator(".note-title")).to_have_value("Počepi in poškodba")
    expect(page.locator(".plan-peek-blanket .md-input")).to_have_value("prvi")


def test_naslov_se_pokaže_v_spodnji_plasti_kretnje_sicer_prva_vrstica(page, base_url):
    start(page, base_url)
    page.locator(".note-title").fill("Počepi")
    # Sosednji zapis brez naslova se označi s prvo vrstico besedila, ne z datumom.
    under = page.locator("#note-peek-future .plan-peek-under-title")
    expect(under).to_have_text("drugi")
    touch = Touch(page)
    touch.hold(195, 400)
    touch.pull(-160)
    touch.raise_(80)
    expect(page.locator(".note-count")).to_have_text("2 / 2")
    touch.up()
    expect(page.locator(".plan-peek-blanket")).not_to_have_class(
        re.compile("is-held|is-leaving")
    )
    touch.hold(195, 400)
    past = page.locator("#note-peek-past")
    expect(past.locator(".plan-peek-under-title")).to_have_text("Počepi")
    expect(past.locator(".plan-peek-under-meta")).to_have_text("2026-10-01 09:00 · Ana")
    touch.up()
