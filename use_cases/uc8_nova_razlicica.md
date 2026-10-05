---
type: use-case
title: "UC8: obvestilo o novi različici"
description: "Nov service worker po namestitvi počaka; trak ponudi osvežitev, različica gradnje je vidna na seznamu strank."
tags: [primer-uporabe, posodobitev, sw]
---

# UC8: obvestilo o novi različici

Nova različica se prenese v ozadju in ne prekine dela: nov worker po namestitvi počaka in trak sporoči, da je na voljo. Šele gumb Osveži ga aktivira in naloži stran znova, po tem, ko se neshranjeno besedilo shrani. Žig gradnje (commit in čas UTC) na seznamu strank določa, katero različico trener ima.

## Sledljivost: obljuba → test

| Obljuba | Test |
| :--- | :--- |
| Worker ne kliče `skipWaiting` sam, samo na sporočilo strani | [sw.test.mjs](../tests/unit_js/sw/sw.test.mjs) |
| Install preveri SHA-256 vsake datoteke iz kataloga gradnje | [sw.test.mjs](../tests/unit_js/sw/sw.test.mjs) |
| Trak »nova različica« se pokaže in Osveži zamenja različico | [test_update.py](../tests/e2e/test_update.py) |
| Žig gradnje je v 24-urni ISO obliki, v razvoju »dev« | [buildInfo.test.mjs](../tests/unit_js/domain/buildInfo.test.mjs) |
| Povezava na zasebnost in različica sta na seznamu strank | [test_layout.py](../tests/medium/test_layout.py) |
