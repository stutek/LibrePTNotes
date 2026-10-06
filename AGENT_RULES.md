---
type: rules
title: "LibrePTNotes: pravila agentov"
description: "Pravila za vse agente (Claude, Gemini, Codex), tudi za seje v oblaku, ki skupnih pravil s Simonovega računalnika nimajo."
tags: [pravila, agenti, oblak]
---

# LibrePTNotes: pravila agentov

Velja za vse agente. Seja v oblaku (claude.ai/code) skupnih pravil s Simonovega računalnika nima, zato je tu vse, kar potrebuje.

## Vrednote

1. **Resnica pred strinjanjem.** Brez hvale in ugibanja; izmerjeno loči od predpostavljenega. Najprej verdikt: ali zahteva izboljša aplikacijo, kaj stane, kaj manjka.
2. **Preprosta aplikacija, stroga kakovost.** Aplikacija je najmanjša, ki opravi delo: brez vaj, sej in programov, brez knjižnic v času izvajanja. Avtomatizacija in preverjanje kakovosti sta na ravni LibrePT; korak gradnje le pripravi objavo (različica, predpomnilnik, celovitost).
3. **En vir resnice.** Specifikacija in odločitve so v `TODO.md`; komentar v kodi pove, zakaj, ne ponavlja specifikacije.
4. **Telefon v eni roki.** Trener piše med vadbo, z eno roko in z motnjami. Rešitev, ki zahteva mizo, je napačna.

## Delo

- **Odločitve, ki jih `TODO.md` ne pokrije, sprejmi sam,** zapiši jih v `TODO.md` §2 z razlogom in jih naštej v telesu commita. Vprašaj le, kadar bi napačna izbira zavrgla delo.
- **Trunk-based za lastnika, PR za prispevke:** Simon in agenti, ki delajo zanj (tudi seja v oblaku), commitajo neposredno na `main` v majhnih commitih, brez vej. Zunanji prispevki pridejo prek pull requesta, ki ga pregleda Simon. Seja v oblaku potisne na `main` po vsakem preverjenem koraku; lokalni agent potisne šele s Simonovo odobritvijo. Objava na Pages teče samo, če testi uspejo.
- **Majhni koraki, vsak preverjen:** za logiko test pred kodo (`tests/unit_js`, `node --test`); pred potiskom `.venv/bin/python -m build check` (kontrole kot v LibrePT; stopnja 5 ZAP potrebuje Docker), za kretnjo in izris preizkus v brskalniku pri širini telefona (390 px). V telesu commita navedi, kaj je bilo preverjeno in kako.
- **Commit:** en logičen korak, sporočilo `type(scope): povzetek` (≤ 72 znakov), telo pove zakaj, zadnja vrstica `Co-Authored-By: <model> <email>`.
- **Čas** v zapisih iz `date` na milisekundo: `date '+%F %T.%N' | cut -c1-23`.
- Vsaka markdown datoteka ima frontmatter (`type`, `title`, `description`, `tags`) in je vpisana v `index.md`.

## Omejitve izdelka

- **Podatki ostanejo v brskalniku** (IndexedDB, baza `libreptnotes`); nič ne gre na strežnik. Domena `stutek.github.io` je ista kot pri LibrePT, zato nobeno ime baze ali ključa ne sme sovpadati z LibrePT.
- **Videz samo v CSS;** koda nastavlja razrede, ne `style`. Izjema je `--plan-pull` v kretnji (prevzeto iz LibrePT).
- **Ura 24-urna, datum ISO** (`YYYY-MM-DD HH:MM`), ne glede na nastavitve telefona.
- **Besedila vmesnika v slovenščini,** zbrana na enem mestu.
