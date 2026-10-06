"""Prvi zagon: dobrodošlica, zasebnostno obvestilo, prva stranka odpre zapis, pripravljen za pisanje."""

import re

from app_helpers import db_state, open_app, seed
from playwright.sync_api import expect

EDITOR = ".plan-peek-blanket .md-input"


def test_prvi_zagon_pokaže_dobrodošlico_in_zasebnostno_obvestilo(page, base_url):
    open_app(page, base_url)
    expect(page.locator(".welcome h1")).to_have_text("Beležke za tvoje stranke")
    expect(page.locator(".add-client")).to_have_class(re.compile("is-welcome"))
    expect(page.locator(".add-client button[type=submit]")).to_have_text(
        "Dodaj prvo stranko"
    )
    expect(page.locator(".notice")).to_contain_text("Tvoje stranke, tvoja odgovornost")
    # Brez strank ni kaj shraniti, obnova z drugega telefona pa mora biti na dosegu.
    expect(page.get_by_role("button", name="Obnovi iz datoteke")).to_be_visible()
    expect(page.get_by_role("button", name="Shrani kopijo")).to_have_count(0)


def test_prva_stranka_odpre_zapis_pripravljen_za_pisanje(page, base_url):
    open_app(page, base_url)
    page.locator("#client-name").fill("Ana Novak")
    page.locator(".add-client button[type=submit]").click()
    expect(page.locator(EDITOR)).to_be_focused()
    expect(page.locator(EDITOR)).to_have_attribute("placeholder", "Piši tukaj …")
    expect(page.locator(".tab.is-active .tab-name")).to_have_text("Ana Novak")
    expect(page.locator(".note-count")).to_have_text("1 / 1")
    page.keyboard.type("takoj pišem")
    state = db_state(page)
    assert [c["name"] for c in state["clients"]] == ["Ana Novak"]
    assert len(state["notes"]) == 1


def test_naslednja_stranka_ostane_na_seznamu(page, base_url):
    seed(page, base_url, [{"name": "Ana", "notes": []}])
    expect(page.locator(".add-client button[type=submit]")).to_have_text("Dodaj")
    expect(page.locator(".welcome")).to_have_count(0)
    page.locator("#client-name").fill("Bor")
    page.locator(".add-client button[type=submit]").click()
    expect(page.locator(".client-name")).to_have_text(["Ana", "Bor"])
    expect(page.locator("#view .client-list")).to_be_visible()
    assert len(db_state(page)["notes"]) == 0


def test_razumem_trajno_skrije_zasebnostno_obvestilo(page, base_url):
    open_app(page, base_url)
    expect(page.locator(".notice")).to_be_visible()
    page.locator(".notice").get_by_role("button", name="Razumem").click()
    expect(page.locator(".notice")).to_have_count(0)
    page.reload()
    expect(page.locator(".welcome")).to_be_visible()
    expect(page.locator(".notice")).to_have_count(0)


def test_stranka_v_seznamu_pokaže_število_zapisov_in_zadnji_datum(page, base_url):
    seed(
        page,
        base_url,
        [
            {
                "name": "Ana",
                "notes": [
                    {"date": "2026-10-01 09:00", "text": "prvi"},
                    {"date": "2026-10-03 18:30", "text": "drugi"},
                ],
            },
            {"name": "Bor", "notes": []},
        ],
    )
    expect(
        page.locator(".client-row", has_text="Ana").locator(".client-meta")
    ).to_have_text("Zapisi: 2 · zadnji 2026-10-03 18:30")
    expect(
        page.locator(".client-row", has_text="Bor").locator(".client-meta")
    ).to_have_text("Še brez zapisov")
