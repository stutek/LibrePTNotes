"""Obvestilo o novi različici: nov worker počaka, trak ponudi Osveži, predpomnilnik se zamenja v celoti."""

import pytest
from app_helpers import (
    cache_names,
    eventually,
    open_app,
    seed,
    wait_for_saved,
    wait_for_service_worker,
    worker_state,
)
from playwright.sync_api import expect

BAR = ".update-bar"
CHECK_UPDATE = (
    "async () => { await (await navigator.serviceWorker.getRegistration()).update(); }"
)


def publish_new_version(site):
    """Nova gradnja: N predpomnilnika +1 in spremenjena datoteka (katalog se izračuna sproti)."""
    site.edit("sw.js", "const CACHE_VERSION = 1;", "const CACHE_VERSION = 2;")
    site.edit(
        "app.css", "/* Videz po LibrePT", "/* NOVA-RAZLIČICA */\n/* Videz po LibrePT"
    )


@pytest.fixture
def running(page, site):
    seed(
        page,
        site.url,
        [{"name": "Ana", "notes": [{"date": "2026-10-01 09:00", "text": "zapis"}]}],
        tabs={"open": ["Ana"], "active": "Ana"},
    )
    wait_for_service_worker(page)
    assert cache_names(page) == ["libreptnotes-v1"]
    return page


def test_brez_nove_različice_ni_traku(running, site):
    running.evaluate(CHECK_UPDATE)
    expect(running.locator(BAR)).to_have_count(0)


def test_nova_različica_pokaže_trak_in_osvežitev_zamenja_predpomnilnik(running, site):
    publish_new_version(site)
    running.evaluate(CHECK_UPDATE)
    bar = running.locator(BAR)
    expect(bar).to_contain_text("Na voljo je nova različica")
    # Nova različica je že prenesena in preverjena, a stara še teče: obe celoti sta v predpomnilniku.
    assert cache_names(running) == ["libreptnotes-v1", "libreptnotes-v2"]
    assert "NOVA-RAZLIČICA" not in running.evaluate(
        "async () => (await fetch('./app.css')).text()"
    )
    assert bar.get_by_role("button", name="Osveži").bounding_box()["height"] >= 44

    bar.get_by_role("button", name="Osveži").click()
    expect(running.locator(BAR)).to_have_count(0)
    eventually(running, lambda: cache_names(running) == ["libreptnotes-v2"])
    eventually(
        running,
        lambda: "NOVA-RAZLIČICA"
        in running.evaluate("async () => (await fetch('./app.css')).text()"),
    )
    assert "NOVA-RAZLIČICA" in running.evaluate(
        "async () => (await fetch('./app.css')).text()"
    )
    expect(running.locator(".plan-peek-blanket .md-input")).to_have_value("zapis")


def test_osvežitev_ne_izgubi_neshranjenega_besedila(running, site):
    publish_new_version(site)
    running.locator(".plan-peek-blanket .md-input").fill("pravkar natipkano")
    running.evaluate(CHECK_UPDATE)
    running.get_by_role("button", name="Osveži").click()
    eventually(running, lambda: cache_names(running) == ["libreptnotes-v2"])
    expect(running.locator(".plan-peek-blanket .md-input")).to_have_value(
        "pravkar natipkano"
    )
    wait_for_saved(running, "Ana", ["pravkar natipkano"])


def test_nepreverljiva_različica_ni_ponujena_in_stara_ostane_celota(
    running, site, context
):
    publish_new_version(site)
    site.corrupt = "app.css"  # katalog pravi drug hash, kot ga ima datoteka
    running.evaluate(CHECK_UPDATE)
    # Namestitev propade; počakamo na stanje delavca, ne na čas.
    eventually(
        running,
        lambda: cache_names(running) == ["libreptnotes-v1"]
        and worker_state(running) == {"installing": False, "waiting": False},
    )
    expect(running.locator(BAR)).to_have_count(0)
    assert cache_names(running) == ["libreptnotes-v1"]
    context.set_offline(True)
    running.reload()
    expect(running.locator(".plan-peek-blanket .md-input")).to_have_value("zapis")
    context.set_offline(False)


def test_osvežitev_zbriše_samo_predpomnilnike_libreptnotes(running, site):
    running.evaluate(
        """async () => {
          for (const name of ["librept-v148", "libreptnotes-v0"]) {
            await (await caches.open(name)).put("./x", new Response("x"));
          }
        }"""
    )
    publish_new_version(site)
    running.evaluate(CHECK_UPDATE)
    running.get_by_role("button", name="Osveži").click()
    eventually(
        running, lambda: cache_names(running) == ["librept-v148", "libreptnotes-v2"]
    )


def test_prva_namestitev_ne_pokaže_traku(page, site):
    open_app(page, site.url)
    wait_for_service_worker(page)
    expect(page.locator(BAR)).to_have_count(0)
