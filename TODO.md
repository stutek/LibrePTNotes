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
3. **Zapisi:** stranka ima več zapisov. Zapis je navadno besedilo z metapodatkom datuma (`YYYY-MM-DD HH:MM`, nastavljen ob ustvarjanju), ki določa vrstni red. Datum je mogoče urediti; čas nastanka (`created`) ostane ločen in se ne spreminja (Simon, 2026-10-05 17:13:50.542).
4. **Kretnja L, enaka kot v LibrePT** (`src/gesture/planPeek.js`): pritisk in zadržanje zoži trenutni zapis; poteg vstran pokaže prejšnji ali naslednji zapis iste stranke pod njim; ko je odkrite vsaj 25 % širine, poteg navzgor za 64 px odpre odkriti zapis; vsak spust brez potega navzgor se vrne nazaj. Kadar je trenutni zapis najnovejši, je na strani naslednjega kartica »Nov zapis«; L jo odpre kot nov zapis s trenutnim datumom.
5. **Barvanje markdowna v urejevalniku:** besedilo ostane navadno; barvajo se naslovi, krepko in ležeče, seznami, citati, koda (vrstična in bloki) in povezave, v barvah teme VS Code (Dark+ ali Light+ po nastavitvi telefona).
6. **Brez povezave:** PWA z imenom LibrePTNotes in lastno ikono; service worker z obsegom `/LibrePTNotes/`; deluje brez povezave.
7. **Objava:** GitHub Pages iz tega repa prek GitHub Actions na `https://stutek.github.io/LibrePTNotes/`; objavi se samo `src/`. Domena ostane `stutek.github.io`, brez lastne domene (Simon, 2026-10-05 11:16:00.450).
8. **Varnostna kopija** (Simon, 2026-10-05 11:16:00.450): enak mehanizem kot v LibrePT. Šifrirana datoteka z geslom v zapisu LibrePT (`src/data/backupFile.js`, `backupEncryption.js`, `passphraseKey.js`, `backupKeyStore.js`): shrani kopijo in obnovi. Ali tudi Google Drive, je odprto (§3).

## 2. Odločitve agenta (preglej)

- **Barvanje brez knjižnice** (2026-10-05 10:53:59.617): prosojen `textarea` nad barvanim `pre`. CodeMirror bi dodal nekaj sto KB kode in odvisnost, ki ju je treba vzdrževati in predpomniti za delo brez povezave.
- **Besedila v slovenščini** (2026-10-05 10:53:59.617).
- **Kretnja kot kopija** (2026-10-05 10:53:59.617): `src/gesture/planPeek.js` in `.css` sta kopiji iz LibrePT (`src/modules/clipboard/planPeek.*`, commit 403715f9, MIT). Repo je ločen, zato se kopija lahko oddalji od LibrePT.
- **Objava samo po uspešnih vratih** (2026-10-05 11:03:59.521; razširjeno 2026-10-05 15:43:08.932): delo teče trunk-based neposredno na `main`, zato Actions pred objavo na Pages požene vseh pet stopenj `python -m build` (kot LibrePT) in ob napaki ne objavi.
- **Relativne poti** (2026-10-05 11:16:00.450): `./sw.js`, obseg service workerja `./`, relativne povezave v manifestu. Aplikacija tako deluje na kateri koli poti in domeni brez spremembe kode.
- **Aplikacija brez knjižnic in brez gradnje, orodja po LibrePT** (2026-10-05 15:43:08.932): v `src/` ni knjižnic; razvojna vrata (Python `build/` + `agent_tools/`, Biome, vendoriran Node) niso del aplikacije. Gradnja samo kopira `src/` v `dist/`, žigosa `version.js` in `sw.js` ter napiše `integrity.json`. Korenskega `package.json` ni (Node ≥ 22.7 zazna ESM).
- **Shramba z zamenljivim backendom** (2026-10-05 09:30:55.822): logika (`src/data/store.js`) ne pozna IndexedDB, backend (`idbBackend.js`) je tanek; Node nima IndexedDB, zato testi uporabijo pomnilniški backend, IDB sloj je preverjen v Chromiumu ročno.
- **Zavihki in trenutni zapis v IndexedDB** (2026-10-05 09:30:55.822): ključ `meta`; `localStorage` se ne uporablja, zato predpona `libreptnotes-` ni potrebna.
- **Service worker kot v LibrePT** (2026-10-05 15:43:08.932, zamenja prejšnjo odločitev o osvežitvi v ozadju): atomsko prednalaganje vseh datotek iz `integrity.json` s preverjanjem SHA-256, nov worker čaka na trak »Na voljo je nova različica«. Število `N` v `libreptnotes-v<N>` prepiše gradnja s številom commitov (`build.stamp_cache_version`), sicer bi ga nihče ne dvignil in novega workerja brskalnik ne bi zaznal. Briše samo `libreptnotes-*`. Test preveri, da je `PRECACHE` seznam nadomeščen z katalogom.
- **Kretnja: blanket in plasti so ustvarjeni enkrat** (2026-10-05 09:30:55.822): `initPlanPeek` obesi poslušalce na `window` in jih ne odstrani. `onOpen` izriše iz pomnilnika sinhrono, shranjuje pozneje (sicer bi se po L najprej pokazal star zapis).
- **Zapis stranke brez zapisov** (2026-10-05 09:30:55.822): kretnje ni (ni trenutnega zapisa), zato je v praznem stanju gumb »Nov zapis«. Prazni zapisi se ne brišejo samodejno.
- **Barve markdowna** (2026-10-05 09:30:55.822): približek Dark+ / Light+ (naslovi, krepko, ležeče, citati, koda, povezave, oznake seznamov); samo barva, brez krepke pisave, da širina znakov ostane enaka. Urejevalnik je enakopisen.
- **Varnostna kopija: vedno šifrirana** (2026-10-05 09:30:55.822): ovojnica je v zapisu LibrePT (`formatVersion` 6), vsebina nosi `app: "libreptnotes"`; obnovitev zavrne datoteko brez te oznake. Obnovitev zamenja vse (kot v LibrePT), po potrditvi. Ključ je v `meta` pod `backupKey`.
- **Urejanje datuma z besedilnim poljem** (2026-10-05 17:13:50.542): dotik datuma v glavi zapisa odpre polje z vrednostjo `YYYY-MM-DD HH:MM`, ki se ob neveljavnem vnosu ne shrani. Ne `datetime-local`, ker telefon v njem prikaže uro po svojih nastavitvah, tudi 12-urno (AGENT_RULES: ura 24-urna). Po spremembi se vrstni red preuredi, zapis ostane trenutni.
- **Brisanje in preimenovanje** (2026-10-05 15:43:08.932, Simon): dodano; ena potrditev (`confirm`/`prompt`), gumb »Izbriši zapis« je zunaj blanketa, da ne ovira kretnje L. Po brisanju zapisa preide trenutni na prejšnjega, sicer na naslednjega.
- **Obseg po LibrePT** (2026-10-05 15:43:08.932, Simon): prevzeta je enaka arhitektura vrat (Python `build/`, ruff, Biome, pip-audit, pytest + Playwright, stopnje 1–5, ZAP). Izpuščeno: onboarding, »star writes«, kartice (Simon), Google Drive, ikone/pisave, demo, `quiet_machine`/`gate_lock`/`snapshot` (obremenitev stroja), `<base href>`/404 (relativne poti, brez usmerjevalnika).
- **Python 3.11** (2026-10-05 15:43:08.932): `.python-version` je 3.11, ker je to Python na razvojnem računalniku in v seji v oblaku (LibrePT ima 3.14); CI teče na isti različici. Playwright je 1.56.0, ker se ujema s predinstaliranim Chromiumom 1194 v oblaku.
- **Vrata sama popravijo oblikovanje** (2026-10-05 15:43:08.932): ruff in Biome pišeta formatiranje in imenujeta spremenjene datoteke, kot LibrePT; ugotovitve, ki zahtevajo presojo, ne.
- **Stopnja 4 = zamrznjene kopije** (2026-10-05 15:43:08.932): `tests/regression/` obnovi `tests/fixtures/backups/*.json` (datoteke se ne spreminjajo), analogno LibrePT-jevi regresiji »izdana shema«.
- **Strožja pravila kot LibrePT** (2026-10-05 15:43:08.932): `inline_styles` dovoli samo `--plan-pull`; `ui_strings` strogo 0 (brez ratcheta); `complexity` prag 15; `unit_coverage` prag 90 % nad `src/domain` in `src/data` (`idbBackend.js` v brskalniku); `import_layers`: domain < data < ui < app, kretnja samostojna.
- **Utrditev uvoza** (2026-10-05 15:43:08.932): `importData` prepiše samo znana polja (`__proto__` in tuja polja ne pridejo v zapise); `kdf.iterations` v datoteki je omejen na 1…10.000.000, da sovražna datoteka ne zamrzne telefona.

## 3. Odprto

- [x] **Varnostna kopija** (2026-10-05 10:53:59.617; odločeno 2026-10-05 11:16:00.450): šifrirana datoteka kot v LibrePT, §1 točka 8.
- [ ] **Google Drive v varnostni kopiji** (2026-10-05 11:16:00.450): LibrePT kopijo pošilja tudi v skrito mapo trenerjevega Google Drive (`drive.appdata`) s svojim Googlovim odjemalcem; na isti domeni bi ga LibrePTNotes lahko uporabil, a bi pisal v isto skrito mapo kot LibrePT (potrebno svoje ime datoteke), prijava bi kazala ime LibrePT, pravilo »nič ne gre na strežnik« pa bi se spremenilo. *Blokira:* obseg varnostne kopije.
- [ ] **LibrePT briše predpomnilnik LibrePTNotes** (2026-10-05 11:01:54.206): izvor `stutek.github.io` je skupen, LibrePT pa ob vsaki posodobitvi izbriše vse predpomnilnike razen svojih (LibrePT `src/sw/cacheManifest.js` `deleteObsoleteCaches`, `src/controllers/appLifecycleController.js` `clearCachesAndReload` ob napaki celovitosti, ki odregistrira tudi vse service workerje na domeni, torej tudi tega od LibrePTNotes). Po posodobitvi LibrePT se LibrePTNotes brez povezave ne odpre, dokler je enkrat ne odpreš s povezavo. Popravek v LibrePT (Simon odobril 2026-10-05 11:05:06.688): brisati samo ključe s predpono `librept-` (`libreptnotes-` se s to predpono ne ujema) in odregistrirati samo service worker z obsegom LibrePT. Do takrat LibrePTNotes ob vsakem zagonu s povezavo predpomnilnik napolni znova. *Blokira:* zanesljivo delo brez povezave (§1 točka 6); ker domena ostane skupna (2026-10-05 11:16:00.450), je popravek pogoj, ne izboljšava. Predano naslednji seji LibrePT (2026-10-05 12:22:06.476): testa sta napisana, koda ne; stanje v LibrePT `.private/AGENT_SYNC/claude-shared-origin-caches.md`.
- [ ] **LibrePT bi lahko odprl datoteko LibrePTNotes** (2026-10-05 09:30:55.822): ovojnica je ista in geslo isto, zato bi LibrePT datoteko odklenil. Ali njegova obnovitev vsebino zavrne, ker nima njegovih zbirk, v kodi nisem do konca preveril in ni preizkušeno. Priporočilo: LibrePT naj zavrne vsebino z `app` ≠ LibrePT; do takrat datoteke LibrePTNotes ne obnavljaj v LibrePT.
- [ ] **Preizkus na pravem telefonu** (2026-10-05 09:30:55.822): kretnja L, dolg pritisk v urejevalniku (sistemski izbor besedila), tipkovnica, prenos datoteke kopije v PWA na iOS in namestitev PWA niso preizkušeni; preizkus je bil v Chromiumu pri 390 px z emuliranim dotikom.
- [x] **Pages** (2026-10-05 09:30:55.822; preverjeno 2026-10-05 12:23:14.564): `https://stutek.github.io/LibrePTNotes/` vrne 200 z naslovom `LibrePTNotes`, `sw.js` vrne 200; zadnji štirje zagoni objave uspešni.
- [x] **Mešanje različic v predpomnilniku** (2026-10-05 12:23:53.130; rešeno: atomski predpomnilnik iz `integrity.json`, `libreptnotes-v<N>` z N = število commitov)
- [ ] **Videz kot LibrePT** (2026-10-05 17:14:49.964): zdaj ima cela aplikacija barve VS Code in sistemsko pisavo; specifikacija predpisuje barve VS Code samo za markdown v urejevalniku. Predlog: svetla tema po LibrePT `src/modules/themes/daylight.css`, temna po `midnight.css`, po nastavitvi telefona; barve VS Code ostanejo v urejevalniku; samo vrednosti v `src/app.css`, brez pisav LibrePT. *Blokira:* videz; čaka Simonovo odločitev.
- [ ] **Čas v zapisih v slovenskem času** (2026-10-05 17:14:49.964): seja v oblaku piše `date` v UTC (zapisi `09:30:55.822` so po našem času 11:30), zato je vrstni red zapisov v tej datoteki napačen. Predlog pravila v AGENT_RULES: `TZ=Europe/Ljubljana date '+%F %T.%N' | cut -c1-23`, in popravek obstoječih zapisov `09:30:55.822` → `11:30:55.822`. *Blokira:* vrstni red zapisov; čaka Simonovo odločitev.
- [ ] **Stopnja 5 (ZAP)** (2026-10-05 15:43:08.932): v seji v oblaku ni Docker démona, zato `run_owasp_zap_scan` in `deploy/zap/zap-baseline.conf` nista bila nikoli pognana; prvi tek bo v Actions. Pričakuj, da bo treba izjeme v konfiguraciji dopolniti.
- [ ] **Prvi tek vseh stopenj v Actions** (2026-10-05 15:43:08.932): lokalno so stopnje 1–4 zelene (`python -m build check`), v Actions še ni teklo; `pip-audit` in `playwright install` tam tečeta prvič.

## 4. Koraki za sejo v oblaku

1. Ogrodje: `src/index.html`, `src/manifest.webmanifest`, `src/sw.js`, `src/app.js`, CSS; potek GitHub Actions za Pages.
2. Shramba (IndexedDB) s testi `node --test`.
3. Stranke in zavihki.
4. Zapisi z datumom in barvanje markdowna.
5. Kretnja L: priklop `src/gesture/planPeek.js` na zapis.
6. Varnostna kopija s šifrirano datoteko (§1 točka 8) s testi `node --test`; Google Drive ne, dokler §3 ni odločen.
7. Preizkus v brskalniku pri 390 px; v telesu commita opis, kaj je bilo preverjeno.


8. Kontrole kakovosti po LibrePT: `build/`, `agent_tools/`, `deploy/`, stopnje 1–5 v `.github/workflows/deploy.yml`.
9. Dokončanje: brisanje/preimenovanje, obvestilo o novi različici, zasebnost, testne ravni `tests/unit_js`, `medium`, `e2e`, `regression`.

Stanje (2026-10-05 15:43:08.932): koraki 1–9 narejeni; `python -m build check` je lokalno zelen v stopnjah 1–4, stopnja 5 ni preverjena (§3).
