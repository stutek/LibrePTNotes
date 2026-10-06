"""Preimenovanje in brisanje strank, brisanje zapisov (ena potrditev)."""

import pytest
from app_helpers import active_tab, client_menu, db_state, note_menu, seed
from playwright.sync_api import expect

NOTES = [
    {"date": "2026-10-01 09:00", "text": "prvi"},
    {"date": "2026-10-02 09:00", "text": "drugi"},
    {"date": "2026-10-03 09:00", "text": "tretji"},
]


@pytest.fixture
def two_clients(page, base_url):
    clients = [
        {"name": "Ana", "notes": NOTES, "current": 1},
        {"name": "Bor", "notes": [{"date": "2026-10-01 09:00", "text": "borov"}]},
    ]
    ids = seed(page, base_url, clients, tabs={"open": ["Ana", "Bor"], "active": None})
    page.ids = ids
    return page


def answer(page, accept, prompt_text=None):
    """Odgovori na naslednji pogovor in vrne seznam njegovih besedil."""
    seen = []

    def handler(dialog):
        seen.append((dialog.type, dialog.message, dialog.default_value))
        dialog.accept(prompt_text) if accept else dialog.dismiss()

    page.once("dialog", handler)
    return seen


def row(page, name):
    return page.locator(".client-row", has_text=name)


def test_preimenovanje_stranke(two_clients):
    seen = answer(two_clients, True, "  Anja ")
    client_menu(two_clients, "Ana", "Preimenuj")
    expect(row(two_clients, "Anja")).to_be_visible()
    assert seen[0][0] == "prompt"
    assert seen[0][2] == "Ana"  # privzeto staro ime
    assert two_clients.locator(".tab-name").all_inner_texts() == [
        "Stranke",
        "Anja",
        "Bor",
    ]
    names = sorted(c["name"] for c in db_state(two_clients)["clients"])
    assert names == ["Anja", "Bor"]


@pytest.mark.parametrize("accept,text", [(False, None), (True, "   "), (True, "Ana")])
def test_preimenovanje_ki_ne_spremeni_imena(two_clients, accept, text):
    answer(two_clients, accept, text)
    client_menu(two_clients, "Ana", "Preimenuj")
    expect(two_clients.locator(".client-name")).to_have_text(["Ana", "Bor"])


def test_brisanje_stranke_zbriše_zapise_zavihek_in_trenutni_zapis(two_clients):
    seen = answer(two_clients, True)
    client_menu(two_clients, "Ana", "Izbriši stranko")
    expect(two_clients.locator(".client-name")).to_have_text(["Bor"])
    assert seen[0][0] == "confirm"
    assert "Ana" in seen[0][1] and "(3)" in seen[0][1]
    assert two_clients.locator(".tab-name").all_inner_texts() == ["Stranke", "Bor"]
    state = db_state(two_clients)
    assert [n["text"] for n in state["notes"]] == ["borov"]
    assert not [
        m for m in state["meta"] if m["key"] == f"current:{two_clients.ids['Ana']}"
    ]
    assert (
        two_clients.ids["Ana"]
        not in next(m for m in state["meta"] if m["key"] == "tabs")["open"]
    )


def test_brisanje_stranke_se_da_preklicati(two_clients):
    answer(two_clients, False)
    client_menu(two_clients, "Ana", "Izbriši stranko")
    expect(two_clients.locator(".client-name")).to_have_text(["Ana", "Bor"])
    assert len(db_state(two_clients)["notes"]) == 4


def open_ana(page):
    page.locator(".tab-name", has_text="Ana").click()
    page.wait_for_selector(".plan-peek-blanket .md-input")


def test_brisanje_trenutnega_zapisa_odpre_prejšnjega(two_clients):
    open_ana(two_clients)
    expect(two_clients.locator(".plan-peek-blanket .md-input")).to_have_value("drugi")
    seen = answer(two_clients, True)
    note_menu(two_clients, "Izbriši zapis")
    expect(two_clients.locator(".plan-peek-blanket .md-input")).to_have_value("prvi")
    expect(two_clients.locator(".note-count")).to_have_text("1 / 2")
    assert "2026-10-02 09:00" in seen[0][1]
    two_clients.reload()
    expect(two_clients.locator(".plan-peek-blanket .md-input")).to_have_value("prvi")


def test_brisanje_zadnjega_zapisa_pokaže_prazno_stanje(two_clients):
    two_clients.locator(".tab-name", has_text="Bor").click()
    answer(two_clients, True)
    note_menu(two_clients, "Izbriši zapis")
    expect(two_clients.locator("#view .note-empty p")).to_have_text(
        "Ta stranka še nima zapisov."
    )
    assert active_tab(two_clients) == "Bor"  # zavihek ostane odprt


def test_brisanje_zapisa_se_da_preklicati(two_clients):
    open_ana(two_clients)
    answer(two_clients, False)
    note_menu(two_clients, "Izbriši zapis")
    expect(two_clients.locator(".note-count")).to_have_text("2 / 3")
    assert len(db_state(two_clients)["notes"]) == 4


def test_neshranjeno_besedilo_izbrisanega_zapisa_ne_obuja_zapisa(two_clients):
    open_ana(two_clients)
    two_clients.locator(".plan-peek-blanket .md-input").fill("drugi, popravljen")
    answer(two_clients, True)
    note_menu(two_clients, "Izbriši zapis")
    expect(two_clients.locator(".plan-peek-blanket .md-input")).to_have_value("prvi")
    two_clients.locator(
        ".tab-name", has_text="Stranke"
    ).click()  # izplakne čakajoče shranjevanje
    expect(two_clients.locator("#view .client-list")).to_be_visible()
    texts = sorted(n["text"] for n in db_state(two_clients)["notes"])
    assert texts == ["borov", "prvi", "tretji"]


def test_meni_zapisa_je_zunaj_blanketa_kretnje(two_clients):
    # Gumb menija je v glavi zapisa, ki je znotraj blanketa; dotik nanj ne sme biti začetek kretnje L,
    # meni sam pa je spodnji list čez celoten zaslon, ne del zapisa.
    open_ana(two_clients)
    button = two_clients.get_by_role("button", name="Več za zapis")
    assert button.bounding_box()["height"] >= 44
    button.click()
    sheet = two_clients.locator("dialog.sheet[open]")
    expect(sheet.get_by_role("button", name="Izbriši zapis")).to_be_visible()
    box = sheet.bounding_box()
    assert box["y"] + box["height"] <= 780 and box["x"] >= 0
    sheet.get_by_role("button", name="Zapri").click()
    expect(sheet).to_have_count(0)
    assert len(db_state(two_clients)["notes"]) == 4
