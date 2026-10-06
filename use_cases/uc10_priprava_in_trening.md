---
type: use-case
title: "UC10: priprava načrta in trening"
description: "Celoten delovni tok trenerja: odpre stranko, z eno kretnjo začne nov zapis, napiše načrt, med treningom pokuka v prejšnji zapis in dopiše izvedbo; vse ostane po ponovnem nalaganju."
tags: [primer-uporabe, delovni-tok, kretnja]
---

# UC10: priprava načrta in trening

Trener pripravi načrt za stranko, ga na treningu odpre, vmes pogleda, kaj je delala zadnjič, in dopisuje izvedbo. Vse z eno roko in brez razlage: dotik vrstice odpre beležke, kretnja L začne nov zapis, pokukanje v prejšnji zapis se brez posledic vrne.

Scenarij je tudi prikaz: `DEMO_PAUSE=5 .venv/bin/python -m pytest tests/e2e/test_demo_training.py -n0 -s` odpre vidno okno s premorom in napisom po vsakem koraku.

## Sledljivost: obljuba → test

| Obljuba | Test |
| :--- | :--- |
| Seznam strank kaže število zapisov in datum zadnjega; dotik vrstice odpre beležke z zadnjim zapisom | [test_demo_training.py](../tests/e2e/test_demo_training.py) |
| Kretnja L ob najnovejšem zapisu ustvari nov zapis z današnjim datumom | [test_demo_training.py](../tests/e2e/test_demo_training.py) |
| Naslov in seznam vaj se vpišeta in obarvata; pokukanje v prejšnji zapis pokaže njegovo vsebino in se po spustu vrne brez spremembe načrta | [test_demo_training.py](../tests/e2e/test_demo_training.py) |
| Izvedba, rezultati in opomba za naslednjič se dopišejo, po ponovnem nalaganju je vse ostalo | [test_demo_training.py](../tests/e2e/test_demo_training.py) |
