---
type: policy
title: "LibrePTNotes: zasebnost"
description: "Kaj LibrePTNotes shrani, kje in kaj ne zapusti telefona; izvorno besedilo strani src/privacy.html."
tags: [zasebnost, podatki, gdpr]
---

# LibrePTNotes: zasebnost

LibrePTNotes je beležnica za osebne trenerje. Vse, kar vpišeš, ostane v brskalniku tvojega telefona.

## Kaj se shrani

* Imena strank in zapisi o njih (besedilo in datum).
* Odprti zavihki in kateri je izbran.
* Predpomnjene datoteke aplikacije, da deluje brez povezave.
* Če si nastavil geslo za varnostno kopijo: iz njega izpeljan ključ, ki ga brskalnik ne pusti prebrati nazaj (ne geslo samo).

## Kje

Podatki so v brskalnikovi shrambi IndexedDB (baza `libreptnotes`) na tvoji napravi. Aplikacija prosi brskalnik, naj podatkov ne pobriše ob pomanjkanju prostora, in ne pošilja ničesar na strežnik, nima uporabniških računov, sledenja ali analitike in ne nalaga zunanjih skript, pisav ali slik.

## Varnostna kopija

Kopijo shraniš sam kot datoteko. Datoteka je vedno šifrirana z geslom, ki si ga določiš; brez gesla je ni mogoče prebrati in gesla ni mogoče obnoviti. Kam datoteko shraniš ali pošlješ, odločaš ti.

## Brisanje

Podatke izbrišeš tako, da v brskalniku počistiš podatke strani ali odstraniš nameščeno aplikacijo. Brez varnostne kopije jih nihče ne more vrniti.

## Stranke

Zapisi o strankah so osebni podatki tvojih strank. Ker ostanejo na tvoji napravi, si zanje odgovoren sam: zavaruj telefon in varnostne kopije ter stranke obvesti, kaj o njih beležiš.

## Povezave

Specifikacija in koda: [LibrePTNotes na GitHubu](https://github.com/stutek/LibrePTNotes).
