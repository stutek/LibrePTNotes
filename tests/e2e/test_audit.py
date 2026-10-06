"""Samopregled proti specifikaciji: kar bi ob napaki trenerju ostalo skrito ali krhko."""

from playwright.sync_api import expect


def test_brez_shrambe_v_brskalniku_aplikacija_pove_zakaj(page, base_url):
    page.add_init_script(
        "Object.defineProperty(window, 'indexedDB', { value: undefined })"
    )
    page.goto(base_url)
    message = page.locator(".storage-error")
    expect(message).to_be_visible()
    expect(message).to_contain_text("Shramba")
    assert page.locator("#view .client-list, #view .note-page").count() == 0


def test_aplikacija_zaprosi_trajno_shrambo(page, base_url):
    # Brez tega brskalnik ob pomanjkanju prostora lahko pobriše IndexedDB: zapisi trenerja bi izginili.
    page.add_init_script(
        """
        window.__persistRequests = 0;
        Object.defineProperty(navigator, 'storage', { value: {
          persisted: async () => false,
          persist: async () => { window.__persistRequests += 1; return true; },
        } });
        """
    )
    page.goto(base_url)
    page.wait_for_selector("#view .page")
    page.wait_for_function("window.__persistRequests >= 1")
    assert page.evaluate("window.__persistRequests") == 1, (
        "prošnja je ena, ne ena na izris"
    )


def test_neuspelo_shranjevanje_se_vidi_in_ne_izgleda_shranjeno(page, base_url):
    # Najdba raziskovalnega testiranja: ko brskalnik zapre ali izbriše bazo, medtem ko je aplikacija
    # odprta, je tipkanje izgledalo shranjeno, po osvežitvi pa je bilo vse izgubljeno.
    from app_helpers import seed

    seed(
        page,
        base_url,
        [{"name": "Ana", "notes": [{"date": "2026-10-01 09:00", "text": ""}]}],
        tabs={"open": ["Ana"], "active": "Ana"},
    )
    page.wait_for_selector(".md-input")
    expect(page.locator(".save-error")).to_have_count(0)
    cdp = page.context.new_cdp_session(page)
    cdp.send(
        "Storage.clearDataForOrigin",
        {"origin": base_url.split("/LibrePTNotes")[0], "storageTypes": "indexeddb"},
    )
    page.locator(".md-input").fill("to se ne bo shranilo")
    expect(page.locator(".save-error")).to_be_visible()
    expect(page.locator(".save-error")).to_contain_text("Shranjevanje ni uspelo")
