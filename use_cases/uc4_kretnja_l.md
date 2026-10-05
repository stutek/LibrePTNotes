---
type: use-case
title: "UC4: kretnja L"
description: "Pritisk in zadržanje zoži zapis, poteg vstran pokaže soseda, poteg navzgor ga odpre; v najnovejšem zapisu kartica Nov zapis."
tags: [primer-uporabe, kretnja, planpeek]
---

# UC4: kretnja L

Kretnja je enaka kot v LibrePT (`src/gesture/planPeek.js`, kopija). Pritisk in zadržanje zoži trenutni zapis, poteg vstran pokaže prejšnji ali naslednji zapis iste stranke pod njim, ko je odkrite vsaj četrtina širine, poteg navzgor za 64 px odpre odkriti zapis. Vsak spust brez potega navzgor se vrne nazaj. V najnovejšem zapisu je na strani naslednjega kartica »Nov zapis«, ki jo L odpre s trenutnim datumom.

## Sledljivost: obljuba → test

| Obljuba | Test |
| :--- | :--- |
| Zadržanje zoži zapis, spust ga vrne | [test_gesture.py](../tests/e2e/test_gesture.py) |
| Poteg manj kot četrtino ne pripravi odprtja | [test_gesture.py](../tests/e2e/test_gesture.py) |
| Poteg vstran brez potega navzgor ne odpre nič | [test_gesture.py](../tests/e2e/test_gesture.py) |
| Poteg vstran in navzgor odpre prejšnji ali naslednji zapis | [test_gesture.py](../tests/e2e/test_gesture.py) |
| Najstarejši zapis nima prejšnjega, najnovejši ponudi nov zapis s trenutnim datumom | [test_gesture.py](../tests/e2e/test_gesture.py) |
| Kretnja ne sproži urejanja ali izbire besedila | [test_gesture.py](../tests/e2e/test_gesture.py) |
| Sosedje zapisa so iste stranke | [notes.test.mjs](../tests/unit_js/domain/notes.test.mjs) |
