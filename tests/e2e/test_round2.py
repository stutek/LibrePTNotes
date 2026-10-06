"""Drugi krog raziskovalnega testiranja: kar je trener-začetnik zgrešil ali ga je zmedlo."""

import pytest
from app_helpers import Touch, db_state, seed
from playwright.sync_api import expect

NOTES = [
    {"date": "2026-10-01 09:00", "text": "prvi trening", "title": "Uvod"},
    {"date": "2026-10-02 09:00", "text": "# Drugi\nčučanje"},
    {"date": "2026-10-03 09:00", "text": "tretji trening"},
]
EDITOR = ".plan-peek-blanket .md-input"


def start(page, base_url, notes=NOTES, current=1):
    seed(
        page,
        base_url,
        [{"name": "Ana", "notes": notes, "current": current}],
        tabs={"open": ["Ana"], "active": "Ana"},
    )
    expect(page.locator(EDITOR)).to_be_visible()
    return page


def count(page):
    return page.locator(".plan-peek-blanket .note-count").inner_text()


def test_na_strani_ni_besede_null_ali_undefined_po_kretnji_in_potrditvi_namiga(
    page, base_url
):
    # Najdba: po prvi kretnji je nad poljem pisalo »null« (prazen pas namiga je bil vstavljen kot besedilo).
    start(page, base_url, current=2)
    touch = Touch(page)
    touch.hold(195, 400)
    touch.pull(-150)
    touch.raise_(90)
    touch.up()
    expect(page.locator(".note-count")).to_have_text("4 / 4")
    text = page.locator("body").inner_text()
    assert "null" not in text and "undefined" not in text
    page.get_by_role("button", name="Stranke").first.click()
    page.wait_for_selector(".client-list")
    text = page.locator("body").inner_text()
    assert "null" not in text and "undefined" not in text


def test_vidni_gumbi_za_prejsnji_naslednji_in_nov_zapis(page, base_url):
    # Najdba: edina pot do novega in prejšnjega zapisa je bila skrita kretnja; z miško je ni bilo.
    start(page, base_url)
    bar = page.locator(".note-bar")
    expect(bar).to_be_visible()
    prev = bar.get_by_role("button", name="Prejšnji zapis")
    nxt = bar.get_by_role("button", name="Naslednji zapis")
    prev.click()
    expect(page.locator(".note-count")).to_have_text("1 / 3")
    expect(prev).to_be_disabled()
    expect(page.locator(".note-title")).to_have_value("Uvod")
    nxt.click()
    nxt.click()
    expect(page.locator(".note-count")).to_have_text("3 / 3")
    expect(nxt).to_be_disabled()
    expect(page.locator(EDITOR)).to_have_value("tretji trening")
    bar.locator(".note-new").click()
    expect(page.locator(".note-count")).to_have_text("4 / 4")
    expect(page.locator(EDITOR)).to_be_focused()
    page.reload()
    expect(page.locator(".note-count")).to_have_text("4 / 4")


def test_nov_zapis_ob_praznem_zapisu_ne_ustvari_se_enega(page, base_url):
    # Najdba: vsaka kretnja na praznem zapisu je ustvarila nov prazen zapis in seznam se je polnil s praznimi.
    start(page, base_url)
    page.locator(".note-bar .note-new").click()
    expect(page.locator(".note-count")).to_have_text("4 / 4")
    page.locator(".note-bar .note-new").click()
    expect(page.locator(".note-count")).to_have_text("4 / 4")
    touch = Touch(page)
    touch.hold(195, 400)
    touch.pull(-150)
    touch.raise_(90)
    touch.up()
    expect(page.locator(".note-count")).to_have_text("4 / 4")
    expect(page.locator(EDITOR)).to_be_focused()
    assert len(db_state(page)["notes"]) == 4


def test_skok_na_zapis_s_seznamom(page, base_url):
    # Najdba: pri 200 zapisih je bilo do starega zapisa treba narediti toliko kretenj.
    start(page, base_url)
    page.locator(".note-bar .note-jump").click()
    sheet = page.locator("dialog.sheet")
    expect(sheet).to_be_visible()
    items = sheet.locator(".sheet-item:not(.sheet-cancel)")
    assert items.count() == 3
    assert (
        "Uvod" in items.nth(2).inner_text()
        and "2026-10-01 09:00" in items.nth(2).inner_text()
    )
    assert "Drugi" in items.nth(1).inner_text()
    items.nth(2).click()
    expect(page.locator(".note-count")).to_have_text("1 / 3")


def test_nazaj_iz_zapisa_vrne_na_seznam_in_ne_zapusti_aplikacije(page, base_url):
    # Najdba: tipka Nazaj po odprtju zapisa je vrgla iz aplikacije.
    page.goto(base_url)
    page.wait_for_selector("#client-name")
    page.fill("#client-name", "Ana")
    page.locator(".add-client button[type=submit]").click()
    page.wait_for_selector(EDITOR)
    page.go_back()
    expect(page.locator(".client-list")).to_be_visible()
    assert page.url.startswith(base_url.rstrip("/"))
    page.locator(".open-notes").click()
    expect(page.locator(EDITOR)).to_be_visible()
    page.go_back()
    expect(page.locator(".client-list")).to_be_visible()


def test_drugi_zavihek_osveži_besedilo_brez_opozorila_ko_nic_ni_neshranjeno(
    page, base_url
):
    start(page, base_url)
    other = page.context.new_page()
    other.goto(base_url)
    other.wait_for_selector(EDITOR)
    other.locator(EDITOR).fill("pisano v drugem zavihku")
    expect(page.locator(EDITOR)).to_have_value("pisano v drugem zavihku")
    assert "null" not in page.locator("body").inner_text()


def test_podvojeno_ime_stranke_opozori_in_se_doda_ob_ponovnem_potrdilu(page, base_url):
    start(page, base_url)
    page.get_by_role("button", name="Stranke").first.click()
    page.wait_for_selector("#client-name")
    page.fill("#client-name", "ana")
    page.locator(".add-client button[type=submit]").click()
    expect(page.locator(".form-error")).to_contain_text("že obstaja")
    assert len(db_state(page)["clients"]) == 1
    page.locator(".add-client button[type=submit]").click()
    expect(page.locator(".client-name")).to_have_count(2)


def luminance(rgb):
    def channel(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def colors(page, selector):
    return page.locator(selector).first.evaluate(
        """e => {
        const rgb = s => (s.match(/rgba?\\(([^)]+)\\)/) || [,''])[1].split(',').slice(0, 3).map(Number);
        const s = getComputedStyle(e);
        const first = (s.backgroundImage.match(/rgb\\([^)]+\\)/) || [s.backgroundColor])[0];
        return { fg: rgb(s.color), bg: rgb(first) };
    }"""
    )


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_zeleno_besedilo_in_gumbi_imajo_kontrast_vsaj_4_5(
    browser, browser_context_args, base_url, scheme
):
    context = browser.new_context(**{**browser_context_args, "color_scheme": scheme})
    page = context.new_page()
    page.goto(base_url)
    page.wait_for_selector("#client-name")
    for selector in (".add-client button[type=submit]", ".notice .primary"):
        c = colors(page, selector)
        assert contrast(c["fg"], c["bg"]) >= 4.5, (scheme, selector, c)
    page.evaluate(
        "() => document.documentElement.style.setProperty('x','y')"
    ) if False else None
    link = page.locator(".privacy-link").first
    fg = link.evaluate(
        "e => getComputedStyle(e).color.match(/\\d+/g).slice(0,3).map(Number)"
    )
    page_bg = page.evaluate(
        "() => getComputedStyle(document.body).backgroundColor.match(/\\d+/g).slice(0,3).map(Number)"
    )
    assert contrast(fg, page_bg) >= 4.5, (scheme, fg, page_bg)
    context.close()


def test_datum_zapisa_je_cilj_za_dotik_vsaj_44_px(page, base_url):
    start(page, base_url)
    assert page.locator(".note-date").bounding_box()["height"] >= 44
