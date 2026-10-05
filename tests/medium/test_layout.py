"""Stran pri 390 px: brez vodoravnega drsenja, ciljne površine za en prst."""

import pytest
from app_helpers import seed

LONG_NAME = "Zelo dolgo ime stranke brez konca " + "X" * 60
UNBROKEN = "W" * 200
NOTE = "# " + UNBROKEN + "\n" + "beseda " * 80 + "\n```\n" + UNBROKEN + "\n```"


def overflow(page):
    return page.evaluate(
        "() => ({ doc: document.documentElement.scrollWidth, win: innerWidth, body: document.body.scrollWidth })"
    )


@pytest.fixture
def crowded(page, base_url):
    clients = [{"name": f"Stranka {i}", "notes": []} for i in range(8)]
    clients.append(
        {"name": LONG_NAME, "notes": [{"date": "2026-10-01 09:00", "text": NOTE}]}
    )
    seed(
        page,
        base_url,
        clients,
        tabs={"open": [c["name"] for c in clients], "active": None},
    )
    return page


def test_seznam_strank_brez_vodoravnega_drsenja(crowded):
    sizes = overflow(crowded)
    assert sizes["doc"] <= sizes["win"]
    assert sizes["body"] <= sizes["win"]


def test_zapis_z_dolgimi_besedami_brez_vodoravnega_drsenja(crowded):
    crowded.locator(".tab-name", has_text="Zelo dolgo").click()
    crowded.wait_for_selector(".plan-peek-blanket .md-input")
    sizes = overflow(crowded)
    assert sizes["doc"] <= sizes["win"]
    area = crowded.locator(".plan-peek-blanket .md-input")
    assert area.evaluate("e => e.scrollWidth <= e.clientWidth")


def test_vsi_gumbi_so_vsaj_44_px(crowded):
    for button in crowded.locator("#view button:visible, #tabs button:visible").all():
        box = button.bounding_box()
        label = button.inner_text() or button.get_attribute("aria-label")
        assert box["height"] >= 44, label
        assert box["width"] >= 44, label


def test_zavihki_se_prelomijo_v_vrstice_in_stran_ne_drsi(crowded):
    # As in LibrePT, many tabs wrap onto further rows instead of scrolling out of view.
    tabs = crowded.locator("#tabs")
    assert tabs.evaluate("e => e.scrollWidth <= e.clientWidth")
    assert tabs.bounding_box()["height"] > 60
    assert overflow(crowded)["doc"] <= 390


def test_povezava_na_zasebnost_in_različica_sta_na_seznamu(crowded):
    link = crowded.locator("a.privacy-link")
    assert link.get_attribute("href") == "./privacy.html"
    assert link.bounding_box()["height"] >= 44
    assert crowded.locator(".build-info").inner_text().startswith("Različica: ")
