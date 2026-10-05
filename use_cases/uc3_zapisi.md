---
type: use-case
title: "UC3: zapisi stranke"
description: "Stranka ima več zapisov: navadno besedilo z datumom YYYY-MM-DD HH:MM, urejeni po datumu; besedilo se shrani tudi ob hitrem zapiranju."
tags: [primer-uporabe, zapisi]
---

# UC3: zapisi stranke

Zapis je navadno besedilo z datumom ob ustvarjanju (`YYYY-MM-DD HH:MM`, 24-urno, ne glede na nastavitve telefona). Datum določa vrstni red; pri istem datumu odloči čas nastanka. Trener tipka z eno roko in med motnjami, zato se besedilo shrani samo, tudi če strani ne zapre počasi.

## Sledljivost: obljuba → test

| Obljuba | Test |
| :--- | :--- |
| Zapis dobi datum ob ustvarjanju v obliki `YYYY-MM-DD HH:MM` | [store.test.mjs](../tests/unit_js/data/store.test.mjs), [dates.test.mjs](../tests/unit_js/domain/dates.test.mjs) |
| Zapisi so ločeni po strankah in urejeni po datumu, pri istem datumu po času nastanka | [notes.test.mjs](../tests/unit_js/domain/notes.test.mjs), [store.test.mjs](../tests/unit_js/data/store.test.mjs) |
| Besedilo se posodobi, datum ostane | [store.test.mjs](../tests/unit_js/data/store.test.mjs) |
| Besedilo se shrani tudi ob hitrem zapiranju ali menjavi zavihka | [test_flow.py](../tests/e2e/test_flow.py) |
| Stranka brez zapisov ponudi gumb Nov zapis | [test_flow.py](../tests/e2e/test_flow.py) |
