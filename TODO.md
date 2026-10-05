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
7. **Objava:** GitHub Pages iz tega repa prek GitHub Actions na `https://stutek.github.io/LibrePTNotes/`; objavi se samo `src/`. Domena ostane `stutek.github.io`, brez lastne domene (Simon, 2026-10-05 11:16:00.450).
8. **Varnostna kopija** (Simon, 2026-10-05 11:16:00.450): enak mehanizem kot v LibrePT. Šifrirana datoteka z geslom v zapisu LibrePT (`src/data/backupFile.js`, `backupEncryption.js`, `passphraseKey.js`, `backupKeyStore.js`): shrani kopijo in obnovi. Ali tudi Google Drive, je odprto (§3).

## 2. Odločitve agenta (preglej)

- **Barvanje brez knjižnice** (2026-10-05 10:53:59.617): prosojen `textarea` nad barvanim `pre`. CodeMirror bi dodal nekaj sto KB kode in odvisnost, ki ju je treba vzdrževati in predpomniti za delo brez povezave.
- **Besedila v slovenščini** (2026-10-05 10:53:59.617).
- **Kretnja kot kopija** (2026-10-05 10:53:59.617): `src/gesture/planPeek.js` in `.css` sta kopiji iz LibrePT (`src/modules/clipboard/planPeek.*`, commit 403715f9, MIT). Repo je ločen, zato se kopija lahko oddalji od LibrePT.
- **Objava samo po uspešnih testih** (2026-10-05 11:03:59.521): delo teče trunk-based neposredno na `main`, zato potek GitHub Actions pred objavo na Pages požene `node --test` in ob napaki ne objavi. Brez tega bi vsak pokvarjen potisk takoj prišel na spletno stran.
- **Relativne poti** (2026-10-05 11:16:00.450): `./sw.js`, obseg service workerja `./`, relativne povezave v manifestu. Aplikacija tako deluje na kateri koli poti in domeni brez spremembe kode.
- **Brez knjižnice in gradnje, ES moduli** (2026-10-05 09:30:55.822): `src/` se objavi nespremenjen; `package.json` (`type: module`) je samo v korenu zaradi `node --test` in se ne objavi.
- **Shramba z zamenljivim backendom** (2026-10-05 09:30:55.822): logika (`src/data/store.js`) ne pozna IndexedDB, backend (`idbBackend.js`) je tanek; Node nima IndexedDB, zato testi uporabijo pomnilniški backend, IDB sloj je preverjen v Chromiumu ročno.
- **Zavihki in trenutni zapis v IndexedDB** (2026-10-05 09:30:55.822): ključ `meta`; `localStorage` se ne uporablja, zato predpona `libreptnotes-` ni potrebna.
- **Service worker: predpomnilnik najprej, osvežitev v ozadju** (2026-10-05 09:30:55.822): brez koraka gradnje ni številke različice, ki bi jo bilo treba dvigniti; nova različica pride ob naslednjem zagonu. Test preveri, da `PRECACHE` vsebuje vsako datoteko iz `src/`. Briše samo `libreptnotes-*`.
- **Kretnja: blanket in plasti so ustvarjeni enkrat** (2026-10-05 09:30:55.822): `initPlanPeek` obesi poslušalce na `window` in jih ne odstrani. `onOpen` izriše iz pomnilnika sinhrono, shranjuje pozneje (sicer bi se po L najprej pokazal star zapis).
- **Zapis stranke brez zapisov** (2026-10-05 09:30:55.822): kretnje ni (ni trenutnega zapisa), zato je v praznem stanju gumb »Nov zapis«. Prazni zapisi se ne brišejo samodejno.
- **Barve markdowna** (2026-10-05 09:30:55.822): približek Dark+ / Light+ (naslovi, krepko, ležeče, citati, koda, povezave, oznake seznamov); samo barva, brez krepke pisave, da širina znakov ostane enaka. Urejevalnik je enakopisen.
- **Varnostna kopija: vedno šifrirana** (2026-10-05 09:30:55.822): ovojnica je v zapisu LibrePT (`formatVersion` 6), vsebina nosi `app: "libreptnotes"`; obnovitev zavrne datoteko brez te oznake. Obnovitev zamenja vse (kot v LibrePT), po potrditvi. Ključ je v `meta` pod `backupKey`.
- **Brez brisanja strank in zapisov** (2026-10-05 09:30:55.822): specifikacija ga ne omenja; dodano ni.

## 3. Odprto

- [x] **Varnostna kopija** (2026-10-05 10:53:59.617; odločeno 2026-10-05 11:16:00.450): šifrirana datoteka kot v LibrePT, §1 točka 8.
- [ ] **Google Drive v varnostni kopiji** (2026-10-05 11:16:00.450): LibrePT kopijo pošilja tudi v skrito mapo trenerjevega Google Drive (`drive.appdata`) s svojim Googlovim odjemalcem; na isti domeni bi ga LibrePTNotes lahko uporabil, a bi pisal v isto skrito mapo kot LibrePT (potrebno svoje ime datoteke), prijava bi kazala ime LibrePT, pravilo »nič ne gre na strežnik« pa bi se spremenilo. *Blokira:* obseg varnostne kopije.
- [ ] **LibrePT briše predpomnilnik LibrePTNotes** (2026-10-05 11:01:54.206): izvor `stutek.github.io` je skupen, LibrePT pa ob vsaki posodobitvi izbriše vse predpomnilnike razen svojih (LibrePT `src/sw/cacheManifest.js` `deleteObsoleteCaches`, `src/controllers/appLifecycleController.js` `clearCachesAndReload` ob napaki celovitosti, ki odregistrira tudi vse service workerje na domeni, torej tudi tega od LibrePTNotes). Po posodobitvi LibrePT se LibrePTNotes brez povezave ne odpre, dokler je enkrat ne odpreš s povezavo. Popravek v LibrePT (Simon odobril 2026-10-05 11:05:06.688): brisati samo ključe s predpono `librept-` (`libreptnotes-` se s to predpono ne ujema) in odregistrirati samo service worker z obsegom LibrePT. Do takrat LibrePTNotes ob vsakem zagonu s povezavo predpomnilnik napolni znova. *Blokira:* zanesljivo delo brez povezave (§1 točka 6); ker domena ostane skupna (2026-10-05 11:16:00.450), je popravek pogoj, ne izboljšava.
- [ ] **LibrePT bi lahko odprl datoteko LibrePTNotes** (2026-10-05 09:30:55.822): ovojnica je ista in geslo isto, zato bi LibrePT datoteko odklenil. Ali njegova obnovitev vsebino zavrne, ker nima njegovih zbirk, v kodi nisem do konca preveril in ni preizkušeno. Priporočilo: LibrePT naj zavrne vsebino z `app` ≠ LibrePT; do takrat datoteke LibrePTNotes ne obnavljaj v LibrePT.
- [ ] **Preizkus na pravem telefonu** (2026-10-05 09:30:55.822): kretnja L, dolg pritisk v urejevalniku (sistemski izbor besedila), tipkovnica, prenos datoteke kopije v PWA na iOS in namestitev PWA niso preizkušeni; preizkus je bil v Chromiumu pri 390 px z emuliranim dotikom.
- [ ] **Pages** (2026-10-05 09:30:55.822): potek Actions teče in testi uspejo; ali je Pages vklopljen na »GitHub Actions« in stran na `https://stutek.github.io/LibrePTNotes/` odgovarja, v oblaku ni preverjeno.

## 4. Koraki za sejo v oblaku

1. Ogrodje: `src/index.html`, `src/manifest.webmanifest`, `src/sw.js`, `src/app.js`, CSS; potek GitHub Actions za Pages.
2. Shramba (IndexedDB) s testi `node --test`.
3. Stranke in zavihki.
4. Zapisi z datumom in barvanje markdowna.
5. Kretnja L: priklop `src/gesture/planPeek.js` na zapis.
6. Varnostna kopija s šifrirano datoteko (§1 točka 8) s testi `node --test`; Google Drive ne, dokler §3 ni odločen.
7. Preizkus v brskalniku pri 390 px; v telesu commita opis, kaj je bilo preverjeno.

Stanje (2026-10-05 09:30:55.822): koraki 1–6 so narejeni in preverjeni z `node --test` ter v Chromiumu pri 390 px; korak 7 je opravljen v Chromiumu (ne na telefonu), glej §3.
