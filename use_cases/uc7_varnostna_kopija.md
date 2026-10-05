---
type: use-case
title: "UC7: varnostna kopija"
description: "Šifrirana datoteka z geslom v zapisu LibrePT: shrani kopijo, obnovi iz datoteke; tuje datoteke se zavrnejo."
tags: [primer-uporabe, varnostna-kopija, sifriranje]
---

# UC7: varnostna kopija

Trener shrani kopijo vseh strank in zapisov v datoteko, ki je vedno šifrirana z geslom v zapisu LibrePT (šest besed, zapiše ga na papir). Kopijo odpre na novem telefonu z istim geslom; obnovitev zamenja vse po potrditvi. Datoteka druge aplikacije ali spremenjena datoteka se zavrne in baza ostane nespremenjena.

## Sledljivost: obljuba → test

| Obljuba | Test |
| :--- | :--- |
| Preneseno datoteko tvori šifrirana ovojnica brez čistopisa | [test_backup.py](../tests/e2e/test_backup.py), [backup.test.mjs](../tests/unit_js/data/backup.test.mjs) |
| Na isti napravi se kopija vrne brez vprašanja za geslo | [test_backup.py](../tests/e2e/test_backup.py), [backup.test.mjs](../tests/unit_js/data/backup.test.mjs) |
| Nov telefon: napačno geslo je zavrnjeno, pravo sprejeto | [test_backup.py](../tests/e2e/test_backup.py), [backup.test.mjs](../tests/unit_js/data/backup.test.mjs) |
| Obnovitev zamenja vse; preklic potrditve ne spremeni nič | [test_backup.py](../tests/e2e/test_backup.py), [backup.test.mjs](../tests/unit_js/data/backup.test.mjs) |
| Tuja ali spremenjena datoteka je zavrnjena | [test_backup.py](../tests/e2e/test_backup.py), [backup.test.mjs](../tests/unit_js/data/backup.test.mjs) |
| Dialog z geslom ponudi geslo iz šestih besed v celoti in se prilega zaslonu | [test_password_dialog.py](../tests/medium/test_password_dialog.py) |
| Prazno geslo dialoga ne zapre | [test_password_dialog.py](../tests/medium/test_password_dialog.py) |
| Google Drive ni del kopije | **Ni zgrajeno**: odločitev je odprta, glej TODO.md |
