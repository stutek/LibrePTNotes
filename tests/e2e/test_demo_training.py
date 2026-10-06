"""Priprava načrta in trening: celoten delovni tok trenerja v enem scenariju.

Hkrati test (privzeto, brez premorov, v CI) in prikaz: z `DEMO_PAUSE=5` se odpre vidno okno, po vsakem
koraku je premor (sekunde) in na dnu zaslona napis koraka. Napis vstavi skripta v stran, ki ga CSP
aplikacije zavrne, zato prikaz uporabi kontekst z `bypass_csp`; navaden tek CSP ne spreminja.

    DEMO_PAUSE=5 .venv/bin/python -m pytest tests/e2e/test_demo_training.py -n0 -s

`DEMO_HEADLESS=1` izvede prikaz z napisi brez okna (preverjanje poti prikaza na strežniku brez zaslona).
"""

import os
import re

import pytest
from app_helpers import Touch, wait_for_saved
from playwright.sync_api import expect

PAUSE = float(os.environ.get("DEMO_PAUSE") or 0)
EDITOR = ".plan-peek-blanket .md-input"
TITLE = ".plan-peek-blanket .note-title"
PAST = "#note-peek-past"
CAPTION_JS = """
text => {
  let box = document.getElementById('demo-caption');
  if (!box) {
    box = document.createElement('div');
    box.id = 'demo-caption';
    box.setAttribute('style', 'position:fixed;left:8px;right:8px;bottom:8px;z-index:99999;padding:10px 12px;'
      + 'border-radius:10px;background:#111;color:#fff;font:600 15px/1.3 system-ui;text-align:center;opacity:.92');
    document.body.append(box);
  }
  box.textContent = text;
}
"""


@pytest.fixture
def scenario(playwright, browser, browser_context_args, base_url):
    """Navaden `page` v testu; v prikazu vidno okno z napisi in premori."""
    if PAUSE:
        launched = playwright.chromium.launch(
            headless=bool(os.environ.get("DEMO_HEADLESS")), slow_mo=120
        )
        context = launched.new_context(**{**browser_context_args, "bypass_csp": True})
    else:
        launched = None
        context = browser.new_context(**browser_context_args)
    page = context.new_page()
    page.goto(base_url)
    page.wait_for_selector("#client-name")
    yield page
    context.close()
    if launched:
        launched.close()


def step(page, caption):
    """Napis koraka in premor; v testu je no-op."""
    if not PAUSE:
        return
    page.evaluate(CAPTION_JS, caption)
    page.wait_for_timeout(int(PAUSE * 1000))


def write(page, text):
    """Dopiše besedilo na konec zapisa, kot bi tipkal."""
    editor = page.locator(EDITOR)
    editor.click()
    editor.press("ControlOrMeta+End")
    editor.press_sequentially(text, delay=25 if PAUSE else 0)


def set_date(page, value):
    page.locator(".note-date").click()
    field = page.locator(".note-date-input")
    field.fill(value)
    field.press("Enter")
    expect(page.locator(".note-date span").first).to_have_text(value)


def gesture_new_note(page):
    touch = Touch(page)
    touch.hold(195, 400)
    touch.pull(-150)
    touch.raise_(90)
    touch.up()


def peek_previous(page):
    """Zadrži, povleci desno in pokukaj; vrne vsebino spodnje plasti. Spust brez poteze navzgor."""
    touch = Touch(page)
    touch.hold(195, 400)
    touch.pull(150)
    page.wait_for_selector(f"{PAST}.is-side-chosen")
    shown = page.locator(PAST).inner_text()
    step(page, "Pokukaš v prejšnji zapis; spustiš, ne da bi povlekel navzgor")
    touch.up()
    expect(page.locator(".plan-peek-blanket")).not_to_have_class(
        re.compile(r"is-held|is-leaving|is-springing")
    )
    return shown


def count(page):
    return page.locator(".note-count").inner_text()


def test_priprava_nacrta_in_trening(scenario):
    page = scenario
    today = page.evaluate(
        "() => { const d = new Date(); const p = n => String(n).padStart(2, '0');"
        " return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`; }"
    )

    # Priprava brez napisov: Ana Novak z dvema starima zapisoma, vneseno prek vmesnika.
    page.fill("#client-name", "Ana Novak")
    page.locator(".add-client button[type=submit]").click()
    page.wait_for_selector(EDITOR)
    set_date(page, "2026-09-29 18:00")
    write(page, "# Prvi trening\nsplošna priprava, 3 serije počepov")
    gesture_new_note(page)
    expect(page.locator(".note-count")).to_have_text("2 / 2")
    set_date(page, "2026-10-02 18:00")
    write(page, "# Drugi trening\npočepi 5x5 @ 70 kg, hrbet boli ob koncu")
    wait_for_saved(
        page,
        "Ana Novak",
        [
            "# Prvi trening\nsplošna priprava, 3 serije počepov",
            "# Drugi trening\npočepi 5x5 @ 70 kg, hrbet boli ob koncu",
        ],
    )
    page.reload()
    page.wait_for_selector(EDITOR)

    # 1: seznam strank
    page.get_by_role("button", name="Stranke").first.click()
    page.wait_for_selector(".client-list")
    step(page, "1 · Seznam strank: Ana Novak ima dva zapisa")
    expect(page.locator(".client-meta")).to_contain_text("Zapisi: 2")
    expect(page.locator(".client-meta")).to_contain_text("zadnji 2026-10-02 18:00")

    # 2: dotik vrstice odpre beležke
    page.locator(".open-notes").click()
    page.wait_for_selector(EDITOR)
    step(page, "2 · Dotik vrstice odpre beležke: zadnji zapis, 2. 10.")
    expect(page.locator(".note-date span").first).to_have_text("2026-10-02 18:00")
    expect(page.locator(".note-count")).to_have_text("2 / 2")

    # 3: kretnja L levo in navzgor: nov zapis s trenutnim datumom
    gesture_new_note(page)
    step(
        page, "3 · Kretnja L (vstran, nato navzgor) odpre nov zapis z današnjim datumom"
    )
    expect(page.locator(".note-count")).to_have_text("3 / 3")
    assert page.locator(".note-date span").first.inner_text().startswith(today)

    # 4: načrt
    page.locator(TITLE).fill("Načrt: noge in hrbet")
    write(page, "- počepi 3x5\n- mrtvi dvig 3x5\n- veslanje 3x8")
    step(page, "4 · Napišeš načrt: naslov in seznam vaj")
    expect(
        page.locator(".md-highlight .md-marker").first
    ).to_be_visible()  # seznam je obarvan

    # 5: pokukaš v prejšnji zapis in se vrneš
    shown = peek_previous(page)
    assert "2026-10-02 18:00" in shown and "Drugi trening" in shown
    expect(page.locator(".note-count")).to_have_text("3 / 3")
    expect(page.locator(EDITOR)).to_have_value(
        "- počepi 3x5\n- mrtvi dvig 3x5\n- veslanje 3x8"
    )
    step(page, "5 · Kartica se po spustu vrne: načrt je nespremenjen")

    # 6-11: trening, vmes še en pogled nazaj
    write(page, "\n\n## Izvedba\n- počepi: 5/5/5 @ 80 kg")
    step(page, "6 · Med treningom dopišeš izvedbo pod načrt")
    peek_previous(page)
    write(page, "\n- mrtvi dvig: 5/5/4 @ 100 kg")
    write(page, "\n- veslanje: 8/8/8 @ 50 kg")
    step(page, "7 · Rezultati vaj")
    expect(page.locator(".note-count")).to_have_text("3 / 3")

    # 12: opomba za naslednjič kot citat
    write(page, "\n\n> Naslednjič: poglej tehniko pri mrtvem dvigu")
    expect(page.locator(".md-highlight .md-quote")).to_be_visible()
    step(page, "8 · Opomba za naslednjič kot citat (obarvan)")

    # 13: ponovno nalaganje, vse ostane
    wait_for_saved(
        page,
        "Ana Novak",
        [
            "# Prvi trening\nsplošna priprava, 3 serije počepov",
            "# Drugi trening\npočepi 5x5 @ 70 kg, hrbet boli ob koncu",
            page.locator(EDITOR).input_value(),
        ],
    )
    page.reload()
    page.wait_for_selector(EDITOR)
    expect(page.locator(".note-count")).to_have_text("3 / 3")
    expect(page.locator(TITLE)).to_have_value("Načrt: noge in hrbet")
    text = page.locator(EDITOR).input_value()
    for part in (
        "- počepi 3x5",
        "## Izvedba",
        "mrtvi dvig: 5/5/4 @ 100 kg",
        "> Naslednjič:",
    ):
        assert part in text, part
    step(page, "9 · Po ponovnem nalaganju je vse ostalo")
