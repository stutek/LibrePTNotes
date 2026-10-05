---
type: use-case
title: "UC9: brisanje in preimenovanje"
description: "Preimenovanje in brisanje strank ter brisanje zapisov, vedno po potrditvi in z možnostjo preklica."
tags: [primer-uporabe, brisanje, preimenovanje]
---

# UC9: brisanje in preimenovanje

Trener popravi ime stranke ali pobriše stranko ali zapis. Brisanje stranke zbriše njene zapise, zavihek in trenutni zapis, drugih ne; vsako brisanje se da preklicati s potrditvijo. Po brisanju trenutnega zapisa se odpre prejšnji; po brisanju zadnjega se pokaže prazno stanje. Neshranjeno besedilo izbrisanega zapisa ga ne obudi.

## Sledljivost: obljuba → test

| Obljuba | Test |
| :--- | :--- |
| Preimenovanje obreže ime; prazno ali neznano ime se zavrne | [test_manage.py](../tests/e2e/test_manage.py), [store.test.mjs](../tests/unit_js/data/store.test.mjs) |
| Brisanje stranke zbriše zapise, zavihek in trenutni zapis | [test_manage.py](../tests/e2e/test_manage.py), [store.test.mjs](../tests/unit_js/data/store.test.mjs) |
| Brisanje stranke in zapisa se da preklicati | [test_manage.py](../tests/e2e/test_manage.py) |
| Po brisanju trenutnega zapisa se odpre prejšnji, po zadnjem prazno stanje | [test_manage.py](../tests/e2e/test_manage.py), [store.test.mjs](../tests/unit_js/data/store.test.mjs) |
| Neshranjeno besedilo izbrisanega zapisa ga ne obudi | [test_manage.py](../tests/e2e/test_manage.py) |
| Gumb za brisanje zapisa je zunaj blanketa kretnje | [test_manage.py](../tests/e2e/test_manage.py) |
