---
type: use-case
title: "UC6: delo brez povezave"
description: "PWA z lastnim imenom in ikono, service worker z obsegom ./; aplikacija se zažene in dela brez povezave."
tags: [primer-uporabe, pwa, brez-povezave]
---

# UC6: delo brez povezave

V telovadnici ni signala. Aplikacija se po prvem obisku zažene in dela brez povezave; podatki ostanejo v brskalniku in ne gredo na strežnik. Poti so relativne, zato deluje na kateri koli poti. Ime predpomnilnika je `libreptnotes-v<N>`, da LibrePT na isti domeni ne izbriše njenega.

## Sledljivost: obljuba → test

| Obljuba | Test |
| :--- | :--- |
| Predpomnilnik vsebuje vsako datoteko iz kataloga gradnje | [test_offline.py](../tests/e2e/test_offline.py) |
| Zagon in delo brez povezave | [test_offline.py](../tests/e2e/test_offline.py) |
| Brez povezave se naloži tudi naslov mape in `index.html` | [test_offline.py](../tests/e2e/test_offline.py) |
| Podatki ostanejo v brskalniku in ne gredo na strežnik | [test_offline.py](../tests/e2e/test_offline.py) |
| Predpomnilnik se imenuje `libreptnotes-v<N>`, poti so relativne, manifest ima svoje ime | [sw.test.mjs](../tests/unit_js/sw/sw.test.mjs) |
| Baza in predpomnilnik ne trčita z LibrePT | [test_flow.py](../tests/e2e/test_flow.py) |
| Aplikacija zaprosi trajno shrambo; brez IndexedDB pove razlog namesto prazne strani | [storageDurability.test.mjs](../tests/unit_js/data/storageDurability.test.mjs), [test_audit.py](../tests/e2e/test_audit.py) |
