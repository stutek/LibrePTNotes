"""Delo brez povezave: predpomnilnik vsebuje celotno aplikacijo, zagon in delo ne potrebujeta omrežja."""

import json

from app_helpers import (
    cache_names,
    db_state,
    notes_of,
    open_app,
    seed,
    wait_for_saved,
    wait_for_service_worker,
)
from playwright.sync_api import expect

CACHED_JS = """async () => {
  const cache = await caches.open("libreptnotes-v1");
  return (await cache.keys()).map((r) => new URL(r.url).pathname.split("/LibrePTNotes/")[1]);
}"""


def test_predpomnilnik_vsebuje_vsako_datoteko_iz_kataloga(page, base_url):
    open_app(page, base_url)
    wait_for_service_worker(page)
    assert cache_names(page) == ["libreptnotes-v1"]
    catalog = json.loads(
        page.evaluate(
            "async () => JSON.stringify(await (await fetch('./integrity.json')).json())"
        )
    )
    assert catalog["algorithm"] == "SHA-256"
    expected = {p for p in catalog["files"] if p not in ("sw.js", "integrity.json")}
    assert {
        "index.html",
        "app.js",
        "app.css",
        "version.js",
        "gesture/planPeek.js",
    } <= expected
    assert expected <= set(page.evaluate(CACHED_JS))


def test_zagon_in_delo_brez_povezave(page, context, base_url):
    open_app(page, base_url)
    wait_for_service_worker(page)
    context.set_offline(True)
    page.reload()
    expect(page.locator("#client-name")).to_be_visible()
    page.locator("#client-name").fill("Ana")
    page.get_by_role("button", name="Dodaj stranko").click()
    page.get_by_role("button", name="Odpri beležke stranke").click()
    page.get_by_role("button", name="Nov zapis").click()
    page.locator(".plan-peek-blanket .md-input").fill("zapisano v kleti brez signala")
    wait_for_saved(page, "Ana", ["zapisano v kleti brez signala"])

    page.reload()  # tudi po ponovnem zagonu brez povezave je vse tam
    expect(page.locator(".plan-peek-blanket .md-input")).to_have_value(
        "zapisano v kleti brez signala"
    )
    context.set_offline(False)


def test_brez_povezave_se_naloži_tudi_naslov_index_html_in_mape(
    page, context, base_url
):
    seed(page, base_url, [{"name": "Ana", "notes": []}])
    wait_for_service_worker(page)
    context.set_offline(True)
    for url in (base_url, base_url + "index.html"):
        page.goto(url)
        expect(page.locator(".client-name")).to_have_text("Ana")
    context.set_offline(False)


def test_podatki_ostanejo_v_brskalniku_in_ne_gredo_na_strežnik(page, base_url):
    sent = []
    page.on("request", lambda r: sent.append((r.method, r.url, r.post_data)))
    seed(
        page,
        base_url,
        [
            {
                "name": "Skrivna Stranka",
                "notes": [{"date": "2026-10-01 09:00", "text": "skrivnost"}],
            }
        ],
    )
    wait_for_service_worker(page)
    assert notes_of(page, "Skrivna Stranka")[0]["text"] == "skrivnost"
    assert db_state(page)["clients"][0]["name"] == "Skrivna Stranka"
    assert all(method == "GET" for method, _url, _body in sent)
    assert all("skrivnost" not in url and "Skrivna" not in url for _m, url, _b in sent)
    assert all(
        url.startswith(base_url.rsplit("/LibrePTNotes/", 1)[0]) for _m, url, _b in sent
    )


def test_stran_o_zasebnosti_se_odpre_tudi_brez_povezave(page, context, base_url):
    open_app(page, base_url)
    wait_for_service_worker(page)
    context.set_offline(True)
    page.locator("a.privacy-link").click()
    page.wait_for_url("**/privacy.html")
    assert page.title()
    assert page.locator("body").inner_text().strip()
    context.set_offline(False)
