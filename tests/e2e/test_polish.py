"""Popravki po raziskovalnem testiranju: manjše napake, ki trenerja zmedejo ali ga ne zaščitijo."""

import json

import pytest
from app_helpers import seed
from playwright.sync_api import expect

NOTES = [
    {
        "date": "2026-10-01 09:00",
        "text": "Čučanje 3x5 pri 80 kg, hrbet boli ob koncu serije",
    },
    {"date": "2026-10-02 09:00", "text": ""},
]


@pytest.fixture
def ana(page, base_url):
    seed(
        page,
        base_url,
        [{"name": "Ana", "notes": NOTES, "current": 0}, {"name": "Bor"}],
        tabs={"open": ["Ana"], "active": "Ana"},
    )
    page.wait_for_selector(".md-input")
    return page


def test_polje_zapisa_je_vsaj_16_px_da_iphone_ne_poveča_strani(ana):
    size = ana.locator(".plan-peek-blanket .md-input").evaluate(
        "e => parseFloat(getComputedStyle(e).fontSize)"
    )
    assert size >= 16


def test_namig_o_kretnji_pove_tudi_navzgor_in_nov_zapis(ana):
    hint = ana.locator(".note-hint").inner_text()
    assert "navzgor" in hint and "nov" in hint


def test_brisanje_zapisa_pokaže_začetek_besedila(ana):
    seen = []
    ana.once("dialog", lambda d: (seen.append(d.message), d.dismiss()))
    ana.get_by_role("button", name="Izbriši zapis").click()
    assert "Čučanje 3x5" in seen[0]
    assert "2026-10-01 09:00" in seen[0]


def test_nov_zapis_iz_praznega_stanja_fokusira_polje(ana):
    ana.get_by_role("button", name="Stranke").first.click()
    ana.locator(".client-row", has_text="Bor").get_by_role(
        "button", name="Odpri"
    ).click()
    ana.get_by_role("button", name="Nov zapis").click()
    ana.wait_for_selector(".plan-peek-blanket .md-input")
    expect(ana.locator(".plan-peek-blanket .md-input")).to_be_focused()


def test_gumbi_vrstic_imajo_ime_stranke_za_bralnik_zaslona(ana):
    ana.get_by_role("button", name="Stranke").first.click()
    ana.wait_for_selector(".open-notes")
    labels = ana.locator(".open-notes").evaluate_all(
        "els => els.map(e => e.getAttribute('aria-label') || e.textContent)"
    )
    assert len(set(labels)) == 2
    assert any("Ana" in label for label in labels) and any(
        "Bor" in label for label in labels
    )


def test_prazno_ime_stranke_pove_zakaj_se_ne_doda(ana):
    ana.get_by_role("button", name="Stranke").first.click()
    ana.get_by_role("button", name="Dodaj stranko").click()
    expect(ana.locator(".form-error")).to_be_visible()
    ana.locator("#client-name").fill("Cene")
    expect(ana.locator(".form-error")).to_be_hidden()


def test_pozabi_geslo_vpraša_in_ob_zavrnitvi_geslo_ostane(ana):
    ana.get_by_role("button", name="Stranke").first.click()
    ana.get_by_role("button", name="Spremeni geslo").click()
    ana.locator("#pw-confirm").click()
    ana.wait_for_selector("#dialog-password", state="hidden")
    asked = []
    ana.once("dialog", lambda d: (asked.append(d.message), d.dismiss()))
    ana.get_by_role("button", name="Pozabi geslo").click()
    assert asked, "brez vprašanja je geslo izginilo"
    expect(ana.locator(".backup")).to_contain_text("nastavljeno")
    expect(ana.locator(".backup")).not_to_contain_text("ni nastavljeno")


def test_datoteka_novejše_različice_ne_trdi_da_ni_kopija(ana, tmp_path):
    ana.get_by_role("button", name="Stranke").first.click()
    newer = tmp_path / "novejsa.json"
    newer.write_text(
        json.dumps(
            {
                "formatVersion": 99,
                "container": "aes-gcm",
                "ciphertext": "x",
                "kdf": {"iterations": 600000},
            }
        )
    )
    ana.locator("input[type=file]").set_input_files(newer)
    expect(ana.locator(".backup .status")).to_contain_text("novejše")
