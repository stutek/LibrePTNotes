"""Stored XSS: ime stranke in besedilo zapisa se izrišeta kot besedilo, nikoli kot oznake."""

import pytest
from app_helpers import seed

PAYLOAD = '<img src=x onerror="window.__pwned = 1">'
SCRIPT = "<script>window.__pwned = 2</script><b>krepko</b>"


@pytest.fixture
def poisoned(page, base_url):
    clients = [
        {
            "name": PAYLOAD,
            "notes": [
                {"date": "2026-10-01 09:00", "text": SCRIPT},
                {"date": "2026-10-02 09:00", "text": PAYLOAD},
            ],
        },
        {"name": "Ana", "notes": []},
    ]
    seed(page, base_url, clients, tabs={"open": [PAYLOAD], "active": None})
    return page


def assert_no_injected_markup(page):
    assert page.locator("img, script:not([src]), #view b, #tabs b").count() == 0
    assert page.evaluate("window.__pwned") is None


def test_seznam_in_zavihek_kazeta_ime_kot_besedilo(poisoned):
    assert_no_injected_markup(poisoned)
    assert poisoned.locator(".client-name", has_text=PAYLOAD).count() == 1
    assert poisoned.locator(".tab-name", has_text=PAYLOAD).count() == 1


def test_zapis_in_spodnji_plasti_kažeta_besedilo(poisoned):
    poisoned.locator(".tab-name", has_text=PAYLOAD).click()
    poisoned.wait_for_selector(".plan-peek-blanket .md-input")
    assert_no_injected_markup(poisoned)
    # Trenutni je najnovejši (PAYLOAD), prejšnji (SCRIPT) je izrisan v spodnji plasti.
    assert poisoned.locator(".plan-peek-blanket .md-input").input_value() == PAYLOAD
    assert poisoned.locator("#note-peek-past pre").text_content() == SCRIPT
    assert poisoned.locator(".plan-peek-blanket pre").text_content() == PAYLOAD


def test_tipkanje_oznak_ne_ustvari_elementov(poisoned):
    poisoned.locator(".tab-name", has_text=PAYLOAD).click()
    poisoned.wait_for_selector(".plan-peek-blanket .md-input")
    poisoned.locator(".plan-peek-blanket .md-input").fill(PAYLOAD + SCRIPT)
    assert_no_injected_markup(poisoned)


def test_oznake_v_imenu_aria_oznake_ostanejo_besedilo(poisoned):
    label = poisoned.locator(".tab-close").get_attribute("aria-label")
    assert PAYLOAD in label
    assert_no_injected_markup(poisoned)
