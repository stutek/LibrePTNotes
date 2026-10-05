---
type: index
title: "LibrePTNotes: orodja za agente"
description: "Katalog trajnih, repozitorijskih kontrol, ki jih agent požene namesto enkratnega skripta: kaj vsaka preverja, kje teče in kdaj dodati novo."
tags: [index, agent-tools, kontrole]
---

# Orodja za agente (`agent_tools/`)

Kontrole, ki bi jih agent sicer vsako sejo znova napisal kot enkratno lupinsko cev. Enkratni skript stane iste žetone vsakič in nič ne zapusti; kontrola tu je napisana enkrat, pregledana enkrat in teče v vratih za vedno. Postopki in vrata so povzeti po [LibrePT](https://github.com/stutek/LibrePT) in prirejeni temu repozitoriju (slovenski vmesnik, brez gradnje, en sloj podatkov v brskalniku).

Vsaka kontrola teče kot `python -m agent_tools.<ime>`, ne potrebuje omrežja ne brskalnika (razen `unit_coverage`, ki potrebuje Node), izpiše kršitve kot `pot:vrstica  sporočilo` in vrne 1 ob kršitvi. Vsako kliče `build/` kot `main(...)`, ki vrne 0 ali 1.

## Katalog

| Kontrola | Kaj preverja |
| :--- | :--- |
| [doclinks.py](doclinks.py) | Vsaka `.md` ima frontmatter (`type`, `title`, `description`, `tags`) in je vpisana v [index.md](../index.md); relativne povezave in `#sidra` kažejo na obstoječe; `§N` kaže na oštevilčen naslov, `§N točka M` na obstoječo točko. Izjema so CLAUDE.md, AGENTS.md, GEMINI.md (nalagalniki). |
| [todo_hygiene.py](todo_hygiene.py) | TODO.md ostane en vir resnice in kratek: razdelki `## N.` oštevilčeni brez vrzeli, točke v odprtem razdelku so `- [ ]` ali `- [x]`, zaprta točka je ena vrstica (razlog je v razdelku z odločitvami). |
| [todo_refs.py](todo_refs.py) | Nobena datoteka razen TODO.md ne kaže na njegov razdelek (`TODO.md §2`, `TODO.md#…`, golo `§N` v kodi): razdelek se zapre ali preštevilči, datoteka zapiše svoj razlog sama. |
| [catalog_coverage.py](catalog_coverage.py) | [docs/modules.md](../docs/modules.md) našteva vsak `.js`, `.css` in `.html` pod `src/` z opisom in nobenega neobstoječega. |
| [module_headers.py](module_headers.py) | Modul, katerega prva vrstica imenuje pot (`// src/pot.js — opis`), imenuje svojo. Priznana izjema: kopija iz LibrePT (`// Kopija iz LibrePT: …`). |
| [import_layers.py](import_layers.py) | Uvozi tečejo `domain` < `data` < `ui` < `app.js`; `gesture/` je samostojna, `sw.js` brez uvozov, `i18n.js` ga uvozi samo `app.js`; `domain/` ne seže po DOM; vsak uvoz obstaja. |
| [css_tokens.py](css_tokens.py) | Vsak `var(--x)` ima definicijo; svetla in temna tema (`prefers-color-scheme`) definirata iste barvne lastnosti. Izjema: kljuka `--peek-align` v kopiji kretnje. |
| [ui_strings.py](ui_strings.py) | Besedilo vmesnika gre skozi `t()` iz `src/i18n.js`: nobenega slovenskega ali angleškega literala v kodi UI ali v `index.html`; neznan ključ `t("x")` in ključ, ki ga nihče ne bere, sta napaki. Brez ratcheta (osnova 0). |
| [inline_styles.py](inline_styles.py) | Videz samo v CSS: nobenega `el.style.x =` in `style="…"`; edina izjema `--plan-pull` v `src/gesture/planPeek.js`. |
| [complexity.py](complexity.py) | McCabe ≤ 15 na funkcijo v `src/**/*.js` s pravo slovnico (tree-sitter), brez seznama izjem. |
| [unit_coverage.py](unit_coverage.py) | `tests/unit_js/` pod Nodovo pokritostjo drži vsak modul v `src/domain/` in `src/data/` na 90 % vrstic; brskalniški modul navede test, ki ga drži. |
| [test_assertions.py](test_assertions.py) | Testi (`.mjs`, `.js`, pytest) trdijo vedenje, ne mehanike: prazne trditve, testi brez trditve, števci klicev, identiteta namesto vrednosti, iskanje vzorcev v izvornem besedilu `src/`, točni večrazredni nizi, mrtvi števci. Izjema samo z zapisanim razlogom. |
| [use_case_tests.py](use_case_tests.py) | Vsak `use_cases/uc*.md` ima tabelo »obljuba → test«; zadnja celica povezuje test v `tests/` ali se začne z **Ni zgrajeno** / **Zunaj aplikacije**. |
| [python_version.py](python_version.py) | Ena deklaracija Pythona (`.python-version`), ta računalnik na njej, noben delovni tok ne pripne različice dobesedno. |
| [render_docs.py](render_docs.py) | Generira `src/privacy.html` iz [PRIVACY.md](../PRIVACY.md) (brez surovega HTML, brez skript, slogi `src/docs.css`) in pade, če je commitana stran zastarela; `--write` jo zapiše. |
| [pipeline_gates.py](pipeline_gates.py) | Vsak CI posel zapira objavo (en končni posel, vsi ostali v njegovem tranzitivnem `needs`), vsaka kontrola stopnje 1 teče v CI, vrstni red stopenj je kot v `build.PIPELINE_STAGES`, imena poslov navajajo svojo stopnjo. |

Pomožni modul `_tree.py` ni kontrola: poda seznam datotek (tudi še ne commitanih), skupen vsem.

## Kdaj dodati orodje

Dodaj, ko držijo **vsa tri**; sicer samo poženi ukaz:

1. **Teklo bo znova.** Kontrola je vezana na invariant, ki preživi spremembo, ne na enkratni pregled današnje razlike.
2. **Brez nje tiho odpove.** Kar lovi, v pregledu ni vidno: mrtvi `§2` še vedno bere kot pravilen stavek.
3. **Poceni in deterministično.** Analiza datotek, brez omrežja in brskalnika, da gre ob bok linterjem.

Kdor ne drži (2), sodi v testno zbirko; kdor ne drži (3), v višjo stopnjo.

**Dodajanje pomeni vse**: modul z docstringom, ki pove *zakaj* obstaja, vrstico v katalogu zgoraj, preizkus `tests/unit/test_agent_tools_<ime>.py` (pozitiven in negativen primer na umetnem drevesu v `tmp_path`) in, če naj zapira commit, nalogo v `build/`.

## Povezano

* [AGENT_RULES.md](../AGENT_RULES.md) — pravila agentov, ki jim kontrole služijo.
* [TODO.md](../TODO.md) — specifikacija in odločitve.
* [docs/modules.md](../docs/modules.md) — katalog modulov, ki ga drži `catalog_coverage`.
