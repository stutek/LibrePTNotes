---
type: use-case
title: "UC1: stranke"
description: "Trener ima seznam strank in jim doda novo z imenom; obljube s testi, ki jih držijo."
tags: [primer-uporabe, stranke]
---

# UC1: stranke

Trener med vadbo odpre aplikacijo, vidi seznam svojih strank in doda novo, samo z imenom. Seznam je po slovenski abecedi, ime je obrezano in ne sme biti prazno. Podatki so v lastni bazi `libreptnotes`, ločeni od LibrePT.

## Sledljivost: obljuba → test

| Obljuba | Test |
| :--- | :--- |
| Stranko dodam z imenom in se pojavi na seznamu | [test_flow.py](../tests/e2e/test_flow.py) |
| Prazno ime se zavrne, ime se obreže | [test_flow.py](../tests/e2e/test_flow.py), [store.test.mjs](../tests/unit_js/data/store.test.mjs) |
| Seznam je po imenu v slovenski abecedi (Č za C, Ž na koncu) | [store.test.mjs](../tests/unit_js/data/store.test.mjs) |
| Baza se imenuje `libreptnotes` in ne trči z LibrePT | [names.test.mjs](../tests/unit_js/data/names.test.mjs), [test_flow.py](../tests/e2e/test_flow.py) |
| Seznam strank pri 390 px nima vodoravnega drsenja, gumbi so ≥ 44 px | [test_layout.py](../tests/medium/test_layout.py) |
| Prvi zagon: dobrodošlica z enim poljem, prva stranka sama odpre zapis s fokusom; zasebnostno obvestilo za trenerja se potrdi enkrat; seznam kaže število zapisov in datum zadnjega | [test_first_run.py](../tests/e2e/test_first_run.py) |
| GDPR: izvoz zapisov stranke (vpogled, prenosljivost) in izbris vseh podatkov z dvema potrditvama; dotik vrstice odpre beležke | [test_client_tools.py](../tests/e2e/test_client_tools.py), [export.test.mjs](../tests/unit_js/domain/export.test.mjs), [store.test.mjs](../tests/unit_js/data/store.test.mjs) |
