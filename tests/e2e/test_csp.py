"""CSP (meta in glava dev strežnika): aplikacija deluje brez vgrajenih skript in slogov, brez kršitev."""

import re

from app_helpers import Touch, seed, wait_for_service_worker
from playwright.sync_api import expect

NOTES = [
    {"date": "2026-10-01 09:00", "text": "prvi"},
    {"date": "2026-10-02 09:00", "text": "drugi"},
]


def test_aplikacija_deluje_brez_kršitev_csp(page, base_url):
    problems = []
    page.on(
        "console", lambda m: m.type in ("error", "warning") and problems.append(m.text)
    )
    page.on("pageerror", lambda e: problems.append(str(e)))
    seed(
        page,
        base_url,
        [{"name": "Ana", "notes": NOTES}],
        tabs={"open": ["Ana"], "active": "Ana"},
    )
    wait_for_service_worker(page)
    expect(page.locator(".plan-peek-blanket .md-input")).to_have_value("drugi")
    page.get_by_role("button", name="Izbriši zapis").hover()
    page.locator(".tab-name", has_text="Stranke").click()
    page.get_by_role("button", name="Shrani kopijo").click()
    page.wait_for_selector("#dialog-password[open]")
    assert problems == []


def test_poteg_premakne_zapis_prek_css_spremenljivke(page, base_url):
    seed(
        page,
        base_url,
        [{"name": "Ana", "notes": NOTES}],
        tabs={"open": ["Ana"], "active": "Ana"},
    )
    expect(page.locator(".plan-peek-blanket .md-input")).to_be_visible()
    touch = Touch(page)
    touch.hold(195, 400)
    touch.pull(120)
    page.wait_for_function(
        "() => document.querySelector('.plan-peek-blanket').style.getPropertyValue('--plan-pull') !== ''"
    )
    left = page.locator(".plan-peek-blanket").bounding_box()["x"]
    assert (
        left > 100
    )  # zoženi zapis (60 px) in poteg (120 px) delujeta kljub CSP brez inline slogov
    style = page.locator(".plan-peek-blanket").get_attribute("style")
    assert re.fullmatch(r"--plan-pull: -?[\d.]+px;", style), style  # edini inline slog
    touch.up()
