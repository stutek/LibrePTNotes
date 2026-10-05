"""Kretnja L na zapisu: zadržanje, poteg vstran (četrtina širine), poteg navzgor, rob zapisov."""

import re

from app_helpers import Touch, db_state, seed, wait_for_saved
from playwright.sync_api import expect

NOTES = [
    {"date": "2026-10-01 09:00", "text": "prvi"},
    {"date": "2026-10-02 09:00", "text": "drugi"},
    {"date": "2026-10-03 09:00", "text": "tretji"},
]
X, Y = (
    195,
    400,
)  # sredina zaslona: dovolj stran od robov, kjer je telefonova kretnja za nazaj
EDITOR = ".plan-peek-blanket .md-input"
PAST = "#note-peek-past"
FUTURE = "#note-peek-future"


def start(page, base_url, current):
    seed(
        page,
        base_url,
        [{"name": "Ana", "notes": NOTES, "current": current}],
        tabs={"open": ["Ana"], "active": "Ana"},
    )
    expect(page.locator(EDITOR)).to_be_visible()
    return Touch(page)


def current_text(page):
    return page.locator(EDITOR).input_value()


def settled(page):
    """Kretnja je končana: zapis ni več zožen in ne drsi."""
    expect(page.locator(".plan-peek-blanket")).not_to_have_class(
        re.compile(r"is-held|is-leaving|is-springing")
    )


def test_zadržanje_zoži_zapis_in_spust_ga_vrne(page, base_url):
    touch = start(page, base_url, current=1)
    wide = page.locator(".plan-peek-blanket").bounding_box()["width"]
    touch.hold(X, Y)
    page.wait_for_function(
        "(w) => Math.abs(document.querySelector('.plan-peek-blanket').getBoundingClientRect().width - w) < 2",
        arg=wide - 120,
    )
    touch.up()
    settled(page)
    page.wait_for_function(
        "(w) => Math.abs(document.querySelector('.plan-peek-blanket').getBoundingClientRect().width - w) < 2",
        arg=wide,
    )
    assert current_text(page) == "drugi"


def test_poteg_manj_kot_četrtina_ne_pripravi_odprtja(page, base_url):
    touch = start(page, base_url, current=1)
    touch.hold(X, Y)
    touch.pull(60)  # manj kot 25 % od 390 px
    expect(page.locator(PAST)).to_have_class(re.compile("is-side-chosen"))
    expect(page.locator(PAST)).not_to_have_class(re.compile("is-open-ready"))
    touch.raise_(100)  # poteg navzgor brez dovolj odkritega
    touch.up()
    settled(page)
    assert current_text(page) == "drugi"
    assert page.locator(".note-count").inner_text() == "2 / 3"


def test_poteg_vstran_brez_poteza_navzgor_ne_odpre(page, base_url):
    touch = start(page, base_url, current=1)
    touch.hold(X, Y)
    touch.pull(160)
    expect(page.locator(PAST)).to_have_class(re.compile("is-open-ready"))
    assert (
        "prejšnji" in page.locator(f"{PAST} .plan-peek-label-rest").inner_text().lower()
    )
    touch.raise_(30)  # manj kot 64 px
    expect(page.locator(PAST)).to_have_class(re.compile("is-open-ready"))
    touch.up()
    settled(page)
    assert current_text(page) == "drugi"


def test_poteg_vstran_in_navzgor_odpre_prejšnji_zapis(page, base_url):
    touch = start(page, base_url, current=1)
    touch.hold(X, Y)
    touch.pull(160)
    touch.raise_(80)
    expect(page.locator(".note-count")).to_have_text("1 / 3")
    assert current_text(page) == "prvi"
    touch.up()
    settled(page)
    page.reload()
    assert current_text(page) == "prvi"  # trenutni zapis je zapomnjen


def test_poteg_v_drugo_stran_in_navzgor_odpre_naslednji_zapis(page, base_url):
    touch = start(page, base_url, current=1)
    touch.hold(X, Y)
    touch.pull(-160)
    expect(page.locator(FUTURE)).to_have_class(re.compile("is-open-ready"))
    touch.raise_(80)
    expect(page.locator(".note-count")).to_have_text("3 / 3")
    assert current_text(page) == "tretji"
    touch.up()


def test_poteg_brez_zadržanja_deluje_enako(page, base_url):
    touch = start(page, base_url, current=1)
    touch.down(X, Y)
    touch.pull(160)
    touch.raise_(80)
    expect(page.locator(".note-count")).to_have_text("1 / 3")
    touch.up()


def test_najstarejši_zapis_nima_prejšnjega_in_ne_odpre_ničesar(page, base_url):
    touch = start(page, base_url, current=0)
    touch.hold(X, Y)
    touch.pull(200)
    assert (
        page.locator(f"{PAST} .plan-peek-under-empty").inner_text()
        == "Ni prejšnjega zapisa."
    )
    expect(page.locator(PAST)).not_to_have_class(re.compile("is-open-ready"))
    touch.raise_(100)
    touch.up()
    settled(page)
    assert current_text(page) == "prvi"
    assert len(db_state(page)["notes"]) == 3


def test_najnovejši_zapis_ponudi_nov_zapis_in_ga_odpre_s_trenutnim_datumom(
    page, base_url
):
    touch = start(page, base_url, current=2)
    assert page.locator(f"{FUTURE}.has-create-card").count() == 1
    assert (
        "Nov zapis" in page.locator(f"{FUTURE} .plan-peek-create-cell").text_content()
    )
    now_js = """() => {
      const d = new Date(), p = (n) => String(n).padStart(2, "0");
      return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
    }"""
    before = page.evaluate(now_js)
    touch.hold(X, Y)
    touch.pull(-160)
    expect(page.locator(FUTURE)).to_have_class(re.compile("is-open-ready"))
    touch.raise_(80)
    expect(page.locator(".note-count")).to_have_text("4 / 4")
    after = page.evaluate(now_js)
    assert page.locator(".note-date").inner_text() in (before, after)
    assert current_text(page) == ""
    assert page.evaluate("() => document.activeElement?.classList.contains('md-input')")
    touch.up()
    page.keyboard.type("nov zapis")
    wait_for_saved(page, "Ana", ["prvi", "drugi", "tretji", "nov zapis"])


def test_kretnja_ne_sproži_urejanja_ali_izbire_besedila(page, base_url):
    touch = start(page, base_url, current=1)
    touch.hold(X, Y)
    touch.pull(160)
    touch.up()
    settled(page)
    selection = page.evaluate("() => String(getSelection())")
    assert selection == ""
