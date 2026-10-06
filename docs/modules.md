---
type: catalog
title: "LibrePTNotes: katalog modulov"
description: "Zemljevid src/: vsak modul z eno vrstico. Kontrola agent_tools/catalog_coverage.py preveri, da je vsak naštet in da ni naštetih neobstoječih."
tags: [katalog, moduli, src]
---

# Katalog modulov (`src/`)

Vsak `.js`, `.css` in `.html` pod `src/` je tu z eno vrstico. Sloji uvozov (glej [agent_tools/import_layers.py](../agent_tools/import_layers.py)): `domain` < `data` < `ui` < `app.js`; `gesture/`, `i18n.js` in `sw.js` so samostojni.

## Koren

* [src/index.html](../src/index.html) — ogrodje strani: zavihki, pogled in prazen dialog z geslom (besedila vstavi koda).
* [src/app.js](../src/app.js) — vstopna točka: sestavi shrambo, zavihke in pogled; stanje je v shrambi, ne tukaj.
* [src/app.css](../src/app.css) — videz aplikacije in barve obeh tem (svetla, temna po nastavitvi telefona).
* [src/i18n.js](../src/i18n.js) — vsa besedila vmesnika v slovenščini (`STRINGS`, `t()`).
* [src/sw.js](../src/sw.js) — service worker: predpomni vse iz kataloga gradnje in deluje brez povezave.
* [src/fonts/fonts.css](../src/fonts/fonts.css) — pisave DM Sans, Outfit in JetBrains Mono (iz LibrePT, latin + latin-ext), ista izvora kot aplikacija.
* [src/docs.css](../src/docs.css) — slogi generiranih dokumentov (zasebnost), brez zunanjih virov.
* [src/privacy.html](../src/privacy.html) — stran o zasebnosti, generirana iz `PRIVACY.md` (`agent_tools/render_docs.py`).
* [src/version.js](../src/version.js) — žig gradnje (commit in čas), ki ga prepiše gradnja.

## Domena (čista logika)

* [src/domain/dates.js](../src/domain/dates.js) — datum ISO in 24-urna ura, ročno brez `Intl`.
* [src/domain/notes.js](../src/domain/notes.js) — vrstni red zapisov in sosednja zapisa.
* [src/domain/markdown.js](../src/domain/markdown.js) — razdelitev markdowna na odseke z razredom za barvanje.
* [src/domain/buildInfo.js](../src/domain/buildInfo.js) — prikaz žiga gradnje.

## Podatki

* [src/data/store.js](../src/data/store.js) — shramba strank, zapisov in zavihkov, neodvisna od IndexedDB.
* [src/data/idbBackend.js](../src/data/idbBackend.js) — tanek backend IndexedDB (baza `libreptnotes`).
* [src/data/storageDurability.js](../src/data/storageDurability.js) — prošnja brskalniku za trajno shrambo (`navigator.storage.persist`).
* [src/data/backupFile.js](../src/data/backupFile.js) — vsebina varnostne kopije in obnovitev v šifrirani ovojnici.
* [src/data/backupEncryption.js](../src/data/backupEncryption.js) — šifrirana ovojnica kopije, zapis LibrePT.
* [src/data/passphraseKey.js](../src/data/passphraseKey.js) — ključ AES-GCM iz gesla (PBKDF2).
* [src/data/backupKeyStore.js](../src/data/backupKeyStore.js) — kje je ključ kopije na tej napravi.

## Vmesnik

* [src/ui/dom.js](../src/ui/dom.js) — najmanjši pomočnik za gradnjo DOM prek `textContent`.
* [src/ui/tabs.js](../src/ui/tabs.js) — zavihki: seznam strank in odprte stranke.
* [src/ui/clientList.js](../src/ui/clientList.js) — seznam strank, dodajanje in odpiranje beležk stranke.
* [src/ui/noteView.js](../src/ui/noteView.js) — pogled zapisov stranke z urejevalnikom in kretnjo L.
* [src/ui/highlight.js](../src/ui/highlight.js) — izris barvanega markdowna v `pre`.
* [src/ui/backupSection.js](../src/ui/backupSection.js) — odsek varnostne kopije na seznamu strank.
* [src/ui/passwordDialog.js](../src/ui/passwordDialog.js) — dialog z geslom kopije.
* [src/ui/aboutSection.js](../src/ui/aboutSection.js) — podnožje: različica in povezava do zasebnosti.
* [src/ui/updateBar.js](../src/ui/updateBar.js) — trak »nova različica« in osvežitev service workerja.

## Kretnja L (kopija iz LibrePT)

* [src/gesture/planPeek.js](../src/gesture/planPeek.js) — kretnja »odeja«; kopija iz LibrePT, ne spreminjaj.
* [src/gesture/planPeek.css](../src/gesture/planPeek.css) — slogi kretnje; kopija iz LibrePT.
