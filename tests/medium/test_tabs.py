"""Zavihki: izbira samo s klikom; potegi prek zavihkov in zapisa zavihka ne zamenjajo."""

import pytest
from app_helpers import Touch, active_tab, seed

NAMES = ["Ana", "Bor", "Cene"]


@pytest.fixture
def three_tabs(page, base_url):
    clients = [
        {"name": n, "notes": [{"date": "2026-10-01 09:00", "text": f"zapis {n}"}]}
        for n in NAMES
    ]
    seed(page, base_url, clients, tabs={"open": NAMES, "active": "Ana"})
    page.wait_for_selector(".plan-peek-blanket .md-input")
    return page


def test_klik_izbere_zavihek_in_seznam(three_tabs):
    three_tabs.locator(".tab-name", has_text="Bor").click()
    three_tabs.wait_for_function(
        "() => document.querySelector('.plan-peek-blanket .md-input')?.value === 'zapis Bor'"
    )
    assert active_tab(three_tabs) == "Bor"
    three_tabs.locator(".tab-name", has_text="Stranke").click()
    three_tabs.wait_for_selector("#view .client-list")
    assert active_tab(three_tabs) == "Stranke"


def test_poteg_po_vrstici_zavihkov_ne_zamenja_zavihka(three_tabs):
    box = three_tabs.locator("#tabs").bounding_box()
    y = box["y"] + box["height"] / 2
    touch = Touch(three_tabs)
    touch.down(350, y)
    touch.move_to(40, y)
    touch.up()
    assert active_tab(three_tabs) == "Ana"
    touch.down(40, y)
    touch.move_to(350, y)
    touch.up()
    assert active_tab(three_tabs) == "Ana"


def test_poteg_prek_zapisa_ne_zamenja_zavihka(three_tabs):
    touch = Touch(three_tabs)
    for dx in (-200, 200):
        start = 300 if dx < 0 else 90
        touch.down(start, 400)
        touch.move_to(start + dx, 400)
        touch.up()
        three_tabs.wait_for_selector(".plan-peek-blanket:not(.is-held)")
        assert active_tab(three_tabs) == "Ana"
        assert (
            three_tabs.locator(".plan-peek-blanket .md-input").input_value()
            == "zapis Ana"
        )


def test_zavihek_se_zapre_samo_s_klikom_na_križec(three_tabs):
    three_tabs.get_by_role("button", name="Zapri zavihek: Ana").click()
    three_tabs.wait_for_selector("#view .client-list")
    assert three_tabs.locator(".tab-name").all_inner_texts() == [
        "Stranke",
        "Bor",
        "Cene",
    ]
    assert active_tab(three_tabs) == "Stranke"
