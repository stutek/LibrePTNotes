"""Zamrznjene datoteke varnostnih kopij: kar je izdana različica obljubila, mora delovati vedno.

Datoteke v tests/fixtures/backups/ so ustvarjene s kodo ob izidu svoje oblike in se NIKOLI ne
spreminjajo ali nadomeščajo (kot v LibrePT, test_frozen_backup_corpus.py). Sprememba kode, ki bi
pokvarila njihovo obnovitev, je napaka kode, ne datoteke: bralnik mora ostati združljiv nazaj.
Nova različica oblike doda NOVO datoteko in vnos spodaj; stare ostanejo.
"""

import hashlib
import json
from pathlib import Path

import pytest
from app_helpers import db_state, open_app
from playwright.sync_api import expect

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "backups"

CORPUS = {
    "format6-2-stranki.json": {
        "sha256": "cc0ae247b0d1bbbbd235710837bcbfa5b79ca3a094646f87269837406e7c2c7b",
        "password": "zamrznjeno-geslo-1",
        "format": 6,
        "clients": [
            {"id": "fz-001", "name": "Ana Novak", "created": 1791190860000},
            {"id": "fz-002", "name": "Žan Čeh", "created": 1791190920000},
        ],
        "notes": [
            {
                "id": "fz-003",
                "clientId": "fz-001",
                "date": "2026-10-05 09:03",
                "created": 1791190980000,
                "text": "# Počepi\n**80 kg** × 5, *težko*\n- levo koleno\n> opomba\n`tempo 3-1-1`",
            },
            {
                "id": "fz-004",
                "clientId": "fz-001",
                "date": "2026-10-05 09:04",
                "created": 1791191040000,
                "text": "Drugi zapis\n\n```\nblok kode\n```\n[povezava](https://primer.si)",
            },
            {
                "id": "fz-005",
                "clientId": "fz-002",
                "date": "2026-10-05 09:05",
                "created": 1791191100000,
                "text": "",
            },
            {
                "id": "fz-006",
                "clientId": "fz-002",
                "date": "2026-10-05 09:06",
                "created": 1791191160000,
                "text": "Šumniki: čšž ČŠŽ, emoji 💪",
            },
        ],
    },
}


def by_id(rows):
    return sorted(rows, key=lambda row: row["id"])


def test_vsaka_zamrznjena_datoteka_ima_pričakovano_vsebino():
    on_disk = {path.name for path in FIXTURES.glob("*.json")}
    assert on_disk == set(CORPUS), (
        "nova datoteka potrebuje vnos v CORPUS, vnos pa datoteko"
    )


@pytest.mark.parametrize("name", sorted(CORPUS))
def test_datoteka_je_nespremenjena(name):
    digest = hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest()
    assert digest == CORPUS[name]["sha256"], "zamrznjene datoteke se ne spreminjajo"


@pytest.mark.parametrize("name", sorted(CORPUS))
def test_obnovitev_na_novem_profilu_vrne_vso_vsebino(page, base_url, name):
    spec = CORPUS[name]
    envelope = json.loads((FIXTURES / name).read_text())
    assert envelope["formatVersion"] == spec["format"]
    page.on("dialog", lambda d: d.accept())
    open_app(page, base_url)
    page.locator("input[type=file]").set_input_files(FIXTURES / name)
    page.wait_for_selector("#dialog-password[open]")
    page.locator("#pw-value").fill(spec["password"])
    page.locator("#pw-confirm").click()
    expect(page.locator("#view .backup .status")).to_have_text(
        f"Obnovljeno. Stranke: {len(spec['clients'])}, zapisi: {len(spec['notes'])}."
    )
    state = db_state(page)
    assert by_id(state["clients"]) == by_id(spec["clients"])
    # Kopije, napisane pred naslovom zapisa, naslova nimajo: obnova jim da prazen naslov, vse drugo je enako.
    assert by_id(state["notes"]) == by_id(
        [{"title": "", **note} for note in spec["notes"]]
    )


@pytest.mark.parametrize("name", sorted(CORPUS))
def test_obnovljeno_je_vidno_in_odprto_v_urejevalniku(page, base_url, name):
    spec = CORPUS[name]
    page.on("dialog", lambda d: d.accept())
    open_app(page, base_url)
    page.locator("input[type=file]").set_input_files(FIXTURES / name)
    page.wait_for_selector("#dialog-password[open]")
    page.locator("#pw-value").fill(spec["password"])
    page.locator("#pw-confirm").click()
    names = sorted(client["name"] for client in spec["clients"])
    expect(page.locator(".client-name")).to_have_text(names)
    ana = next(c for c in spec["clients"] if c["name"] == "Ana Novak")
    page.locator(".client-row", has_text="Ana Novak").get_by_role(
        "button", name="Odpri beležke stranke"
    ).click()
    newest = [n for n in spec["notes"] if n["clientId"] == ana["id"]][-1]
    expect(page.locator(".plan-peek-blanket .md-input")).to_have_value(newest["text"])
    expect(page.locator(".note-date span").first).to_have_text(newest["date"])
