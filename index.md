---
type: index
title: "LibrePTNotes: kazalo"
description: "Vstopna točka repozitorija za ljudi in agente."
tags: [index]
---

# LibrePTNotes: kazalo

* **[README.md](README.md)** — kaj je LibrePTNotes in kje teče.
* **[AGENT_RULES.md](AGENT_RULES.md)** — pravila za vse agente, tudi za seje v oblaku.
* **[PRIVACY.md](PRIVACY.md)** — zasebnost: kaj se shrani in kaj ne zapusti telefona; izvor strani `src/privacy.html`.
* **[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)** — licenčna obvestila za prevzete pisave (SIL OFL 1.1) in kopijo kretnje (MIT).
* **[docs/modules.md](docs/modules.md)** — katalog modulov v `src/`, vsak z eno vrstico.
* **[agent_tools/INDEX.md](agent_tools/INDEX.md)** — kontrole kakovosti za agente (`python -m agent_tools.<ime>`): kaj preverjajo in kdaj dodati novo.
* **[use_cases/uc1_stranke.md](use_cases/uc1_stranke.md)** — UC1: stranke; vsak primer uporabe ima tabelo »obljuba → test«.
* **[use_cases/uc2_zavihki.md](use_cases/uc2_zavihki.md)** — UC2: zavihki strank.
* **[use_cases/uc3_zapisi.md](use_cases/uc3_zapisi.md)** — UC3: zapisi stranke z datumom.
* **[use_cases/uc4_kretnja_l.md](use_cases/uc4_kretnja_l.md)** — UC4: kretnja L.
* **[use_cases/uc5_barvanje.md](use_cases/uc5_barvanje.md)** — UC5: barvanje markdowna.
* **[use_cases/uc6_brez_povezave.md](use_cases/uc6_brez_povezave.md)** — UC6: delo brez povezave.
* **[use_cases/uc7_varnostna_kopija.md](use_cases/uc7_varnostna_kopija.md)** — UC7: šifrirana varnostna kopija.
* **[use_cases/uc8_nova_razlicica.md](use_cases/uc8_nova_razlicica.md)** — UC8: obvestilo o novi različici.
* **[use_cases/uc9_brisanje_preimenovanje.md](use_cases/uc9_brisanje_preimenovanje.md)** — UC9: brisanje in preimenovanje.
* **[TODO.md](TODO.md)** — specifikacija, odločitve, odprto delo in koraki. *Tudi:* zahteve, kretnja L, markdown, zavihki.
* **[src/gesture/](src/gesture/)** — kretnja L, kopija iz LibrePT.
* **[src/](src/)** — aplikacija, ki se objavi na Pages (brez koraka gradnje).
* **[tests/](tests/)** — testi po ravneh: `unit_js` (node:test), `unit` (pytest, orodja), `medium`, `e2e`, `regression` (Playwright).
* **[build/](build/)** — vrata kakovosti `python -m build` (stopnje 1–5, sestavljanje `dist/`) in statične varnostne preveritve.
* **[deploy/](deploy/)** — lokalni strežnik pod `/LibrePTNotes/` (enake varnostne glave kot v produkciji) in pravila ZAP.
