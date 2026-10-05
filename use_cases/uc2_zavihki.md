---
type: use-case
title: "UC2: zavihki strank"
description: "Gumb Odpri beležke stranke odpre zavihek; izbira samo s klikom, zapiranje z ✕, zavihki ostanejo po ponovnem nalaganju."
tags: [primer-uporabe, zavihki]
---

# UC2: zavihki strank

Trener odpre beležke več strank hkrati in med njimi preklaplja. Zavihek se izbere samo s klikom: poteg po vrstici zavihkov ali prek zapisa nikoli ne zamenja zavihka (kretnja L je namenjena zapisom). Zavihek se zapre samo z ✕. Odprti zavihki in izbrani zavihek ostanejo po ponovnem nalaganju.

## Sledljivost: obljuba → test

| Obljuba | Test |
| :--- | :--- |
| Klik na zavihek ga izbere, prvi zavihek je seznam strank | [test_tabs.py](../tests/medium/test_tabs.py) |
| Poteg po vrstici zavihkov ali prek zapisa ne zamenja zavihka | [test_tabs.py](../tests/medium/test_tabs.py) |
| Zavihek se zapre samo s klikom na ✕ | [test_tabs.py](../tests/medium/test_tabs.py) |
| Odprti zavihki ostanejo po ponovnem nalaganju | [test_flow.py](../tests/e2e/test_flow.py), [store.test.mjs](../tests/unit_js/data/store.test.mjs) |
| Zavihki so v lastnem drsniku, ne premaknejo strani | [test_layout.py](../tests/medium/test_layout.py) |
