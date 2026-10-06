"""Najdbe raziskovalnega testiranja, ki niso spremenile specifikacije: dvojni dotik, drsenje seznama,
isti zapis v dveh zavihkih brskalnika."""

from app_helpers import db_state, seed
from playwright.sync_api import expect


def test_trojni_hitri_dotik_na_dodaj_ustvari_eno_stranko(page, base_url):
    page.goto(base_url)
    page.wait_for_selector("#client-name")
    page.locator("#client-name").fill("Cene")
    page.locator(".add-client button[type=submit]").evaluate(
        "b => { b.click(); b.click(); b.click(); }"
    )
    expect(page.locator(".client-name")).to_have_text(["Cene"])
    assert [c["name"] for c in db_state(page)["clients"]] == ["Cene"]


def test_seznam_strank_obdrži_drsenje_po_vrnitvi_z_zavihka(page, base_url):
    clients = [{"name": f"Stranka {i:02d}"} for i in range(40)]
    seed(page, base_url, clients, tabs={"open": ["Stranka 00"], "active": None})
    page.wait_for_selector(".client-list")
    page.locator(".page").evaluate("e => { e.scrollTop = 900; }")
    page.wait_for_function("document.querySelector('.page').scrollTop > 800")
    page.locator(".tab-name", has_text="Stranka 00").click()
    page.wait_for_selector(".note-page, .note-empty")
    page.locator(".tab-name", has_text="Stranke").click()
    page.wait_for_selector(".client-list")
    top = page.locator(".page").evaluate("e => e.scrollTop")
    assert top > 800, f"seznam se je vrnil na vrh: {top}"


def test_isti_zapis_v_drugem_zavihku_brskalnika_opozori(page, base_url):
    seed(
        page,
        base_url,
        [{"name": "Ana", "notes": [{"date": "2026-10-01 09:00", "text": "prvi"}]}],
        tabs={"open": ["Ana"], "active": "Ana"},
    )
    other = page.context.new_page()
    other.goto(base_url)
    other.wait_for_selector(".plan-peek-blanket .md-input")
    page.wait_for_selector(".plan-peek-blanket .md-input")
    expect(page.locator(".conflict-error")).to_have_count(0)
    other.locator(".plan-peek-blanket .md-input").fill("pisano v drugem zavihku")
    expect(page.locator(".conflict-error")).to_be_visible()
    expect(page.locator(".conflict-error")).to_contain_text("drugem zavihku")


def test_ležeči_telefon_pusti_dovolj_prostora_za_pisanje(
    browser, browser_context_args, base_url
):
    context = browser.new_context(
        **{**browser_context_args, "viewport": {"width": 780, "height": 390}}
    )
    page = context.new_page()
    seed(
        page,
        base_url,
        [{"name": "Ana", "notes": [{"date": "2026-10-01 09:00", "text": "x"}]}],
        tabs={"open": ["Ana"], "active": "Ana"},
    )
    page.wait_for_selector(".plan-peek-blanket .note-body")
    height = page.locator(".plan-peek-blanket .note-body").bounding_box()["height"]
    context.close()
    assert height >= 250, f"prostor za pisanje v ležečem položaju: {height}px"
