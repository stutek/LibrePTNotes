"""Orodja stranke v meniju: izvoz zapisov, brisanje vseh podatkov, dotik vrstice odpre beležke."""

from app_helpers import client_menu, data_menu, db_state, open_client, seed
from playwright.sync_api import expect

CLIENTS = [
    {
        "name": "Ana",
        "notes": [
            {"date": "2026-10-01 09:00", "text": "čučanje 3x5", "title": "Noge"},
            {"date": "2026-10-02 09:00", "text": "hrbet boli"},
        ],
    },
    {"name": "Bor", "notes": [{"date": "2026-10-01 09:00", "text": "borov zapis"}]},
]


def test_izvoz_zapisov_stranke_prenese_besedilo_po_potrditvi(page, base_url, tmp_path):
    seed(page, base_url, CLIENTS)
    asked = []
    page.once("dialog", lambda d: (asked.append(d.message), d.accept()))
    with page.expect_download() as download:
        client_menu(page, "Ana", "Izvozi zapise (besedilo)")
    assert asked and "Ana" in asked[0] and "nešifrirano" in asked[0]
    assert download.value.suggested_filename == "Ana.md"
    path = tmp_path / "izvoz.md"
    download.value.save_as(path)
    text = path.read_text()
    assert text.startswith("# Ana")
    for part in ("čučanje 3x5", "hrbet boli", "Noge", "2026-10-02 09:00"):
        assert part in text
    assert "borov zapis" not in text


def test_izvoz_brez_potrditve_ne_prenese_ničesar(page, base_url):
    seed(page, base_url, CLIENTS)
    downloads = []
    page.on("download", lambda d: downloads.append(d))
    page.once("dialog", lambda d: d.dismiss())
    client_menu(page, "Ana", "Izvozi zapise (besedilo)")
    expect(page.locator("dialog.sheet")).to_have_count(0)
    assert downloads == []


def test_izbris_vseh_podatkov_potrebuje_dve_potrditvi_in_vrne_prvi_zagon(
    page, base_url
):
    seed(page, base_url, CLIENTS, tabs={"open": ["Ana"], "active": None})
    messages = []
    page.on("dialog", lambda d: (messages.append(d.message), d.accept()))
    data_menu(page, "Izbriši vse podatke")
    expect(page.locator(".welcome")).to_be_visible()
    assert len(messages) == 2
    state = db_state(page)
    assert state["clients"] == [] and state["notes"] == []
    expect(page.locator(".tab-name")).to_have_text(["Stranke"])
    expect(page.get_by_role("button", name="Shrani kopijo")).to_have_count(0)


def test_izbris_vseh_podatkov_se_ustavi_pri_drugi_zavrnitvi(page, base_url):
    seed(page, base_url, CLIENTS)
    answers = iter([True, False])
    page.on("dialog", lambda d: d.accept() if next(answers) else d.dismiss())
    data_menu(page, "Izbriši vse podatke")
    expect(page.locator("dialog.sheet")).to_have_count(0)
    assert len(db_state(page)["clients"]) == 2


def test_dotik_vrstice_stranke_odpre_beležke(page, base_url):
    seed(page, base_url, CLIENTS)
    open_client(page, "Bor")
    expect(page.locator(".tab.is-active .tab-name")).to_have_text("Bor")
    expect(page.locator(".plan-peek-blanket .md-input")).to_have_value("borov zapis")
