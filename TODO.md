---
type: todo
title: "LibrePTNotes: specifikacija in odprto delo"
description: "Specifikacija minimalne beležnice s strankami (Simon, 2026-10-05), odločitve agenta, odprte točke in koraki za sejo v oblaku."
tags: [specifikacija, todo, oblak]
---

# LibrePTNotes: specifikacija in odprto delo

## 1. Specifikacija (Simon, 2026-10-05 10:53:59.617)

Minimalna različica [LibrePT](https://github.com/stutek/LibrePT): samo beležnica s strankami. Brez vaj, sej, programov in QR kode.

1. **Stranke:** lastna baza, ločena od LibrePT. Seznam strank; dodajanje stranke z imenom.
2. **Zavihki strank:** gumb »Odpri beležke stranke« doda zavihek te stranke. Zavihek se izbere samo s klikom; prehoda na prejšnji ali naslednji zavihek ni. Zavihek se zapre z ✕; odprti zavihki ostanejo po ponovnem nalaganju.
3. **Zapisi:** stranka ima več zapisov. Zapis je navadno besedilo z metapodatkom datuma (`YYYY-MM-DD HH:MM`, nastavljen ob ustvarjanju), ki določa vrstni red.
4. **Kretnja L, enaka kot v LibrePT** (`src/gesture/planPeek.js`): pritisk in zadržanje zoži trenutni zapis; poteg vstran pokaže prejšnji ali naslednji zapis iste stranke pod njim; ko je odkrite vsaj 25 % širine, poteg navzgor za 64 px odpre odkriti zapis; vsak spust brez potega navzgor se vrne nazaj. Kadar je trenutni zapis najnovejši, je na strani naslednjega kartica »Nov zapis«; L jo odpre kot nov zapis s trenutnim datumom.
5. **Barvanje markdowna v urejevalniku:** besedilo ostane navadno; barvajo se naslovi, krepko in ležeče, seznami, citati, koda (vrstična in bloki) in povezave, v barvah teme VS Code (Dark+ ali Light+ po nastavitvi telefona).
6. **Brez povezave:** PWA z imenom LibrePTNotes in lastno ikono; service worker z obsegom `/LibrePTNotes/`; deluje brez povezave.
7. **Objava:** GitHub Pages iz tega repa prek GitHub Actions na `https://stutek.github.io/LibrePTNotes/`; objavi se samo `src/`.
8. **Varnostna kopija** (Simon, 2026-10-05 11:05:06.688): gumb »Izvozi« prenese vse stranke in zapise kot datoteko JSON; »Uvozi« jih po potrditvi naloži nazaj in nadomesti obstoječe.

## 2. Odločitve agenta (preglej)

- **Barvanje brez knjižnice** (2026-10-05 10:53:59.617): prosojen `textarea` nad barvanim `pre`. CodeMirror bi dodal nekaj sto KB kode in odvisnost, ki ju je treba vzdrževati in predpomniti za delo brez povezave.
- **Besedila v slovenščini** (2026-10-05 10:53:59.617).
- **Kretnja kot kopija** (2026-10-05 10:53:59.617): `src/gesture/planPeek.js` in `.css` sta kopiji iz LibrePT (`src/modules/clipboard/planPeek.*`, commit 403715f9, MIT). Repo je ločen, zato se kopija lahko oddalji od LibrePT.
- **Objava samo po uspešnih testih** (2026-10-05 11:03:59.521): delo teče trunk-based neposredno na `main`, zato potek GitHub Actions pred objavo na Pages požene `node --test` in ob napaki ne objavi. Brez tega bi vsak pokvarjen potisk takoj prišel na spletno stran.

## 3. Odprto

- [x] **Varnostna kopija** (2026-10-05 10:53:59.617; odločeno 2026-10-05 11:05:06.688): izvoz in uvoz JSON, §1 točka 8.
- [ ] **LibrePT briše predpomnilnik LibrePTNotes** (2026-10-05 11:01:54.206): izvor `stutek.github.io` je skupen, LibrePT pa ob vsaki posodobitvi izbriše vse predpomnilnike razen svojih (LibrePT `src/sw/cacheManifest.js` `deleteObsoleteCaches`, `src/controllers/appLifecycleController.js` `clearCachesAndReload` ob napaki celovitosti, ki odregistrira tudi vse service workerje na domeni, torej tudi tega od LibrePTNotes). Po posodobitvi LibrePT se LibrePTNotes brez povezave ne odpre, dokler je enkrat ne odpreš s povezavo. Popravek v LibrePT (Simon odobril 2026-10-05 11:05:06.688): brisati samo ključe s predpono `librept-` (`libreptnotes-` se s to predpono ne ujema) in odregistrirati samo service worker z obsegom LibrePT. Do takrat LibrePTNotes ob vsakem zagonu s povezavo predpomnilnik napolni znova. *Blokira:* zanesljivo delo brez povezave (§1 točka 6).

## 4. Koraki za sejo v oblaku

1. Ogrodje: `src/index.html`, `src/manifest.webmanifest`, `src/sw.js`, `src/app.js`, CSS; potek GitHub Actions za Pages.
2. Shramba (IndexedDB) s testi `node --test`.
3. Stranke in zavihki.
4. Zapisi z datumom in barvanje markdowna.
5. Kretnja L: priklop `src/gesture/planPeek.js` na zapis.
6. Izvoz in uvoz (§1 točka 8) s testi `node --test`.
7. Preizkus v brskalniku pri 390 px; v telesu commita opis, kaj je bilo preverjeno.
