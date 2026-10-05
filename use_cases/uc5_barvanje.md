---
type: use-case
title: "UC5: barvanje markdowna"
description: "Besedilo ostane navadno; barvajo se naslovi, krepko, ležeče, seznami, citati, koda in povezave v barvah Dark+ ali Light+."
tags: [primer-uporabe, markdown, barvanje]
---

# UC5: barvanje markdowna

Urejevalnik je navaden `textarea` nad barvanim `pre`; barvanje nikoli ne spremeni vnesenega besedila. Barve sledijo temi telefona (Dark+ ali Light+). Besedilo, ki bi bilo označba, se prikaže kot besedilo, ne kot element.

## Sledljivost: obljuba → test

| Obljuba | Test |
| :--- | :--- |
| Odseki imajo razrede za naslove, krepko, ležeče, sezname, citate, kodo in povezave | [markdown.test.mjs](../tests/unit_js/domain/markdown.test.mjs), [test_editor.py](../tests/medium/test_editor.py) |
| Združeni odseki so vedno enaki vhodu | [markdown.test.mjs](../tests/unit_js/domain/markdown.test.mjs), [test_editor.py](../tests/medium/test_editor.py) |
| Barvano besedilo in `textarea` sta enako visoka in poravnana znak za znakom | [test_editor.py](../tests/medium/test_editor.py) |
| Barve sledijo temi telefona | [test_editor.py](../tests/medium/test_editor.py) |
| Tipkanje obarva in shrani | [test_editor.py](../tests/medium/test_editor.py) |
| Oznake v imenu ali besedilu ne ustvarijo elementov | [test_xss_sink.py](../tests/medium/test_xss_sink.py) |
