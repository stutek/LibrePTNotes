---
type: policy
title: "LibrePTNotes: zasebnost in GDPR za trenerja"
description: "Kaj LibrePTNotes shrani in kje, kdo je upravljavec podatkov strank in kaj mora trener po GDPR narediti sam; izvorno besedilo strani src/privacy.html."
tags: [zasebnost, podatki, gdpr]
---

# LibrePTNotes: zasebnost in GDPR za trenerja

LibrePTNotes je beležnica za osebne trenerje. Vse, kar vpišeš, ostane v brskalniku tvojega telefona. Avtor aplikacije do tvojih podatkov nima dostopa in jih nikoli ne prejme.

## Kaj se shrani

* Imena strank in zapisi o njih (naslov, besedilo, datum).
* Odprti zavihki in kateri je izbran, ter kateri enkratni namigi so že prikazani.
* Če si nastavil geslo za varnostno kopijo: iz njega izpeljan ključ, ki ga brskalnik ne pusti prebrati nazaj (ne geslo samo).
* Predpomnjene datoteke aplikacije, da deluje brez povezave.

## Kje

Podatki so v brskalnikovi shrambi IndexedDB (baza `libreptnotes`) na tvoji napravi. Aplikacija prosi brskalnik, naj podatkov ne pobriše ob pomanjkanju prostora, in ne pošilja ničesar na strežnik, nima uporabniških računov, sledenja, analitike ali piškotkov in ne nalaga zunanjih skript, pisav ali slik.

## Kdo je odgovoren za podatke strank

**Ti.** Zapisi o strankah so osebni podatki, ti pa si njihov upravljavec po splošni uredbi o varstvu podatkov (GDPR). Ker podatki ostanejo na tvoji napravi, LibrePTNotes ni obdelovalec in jih ne more varovati namesto tebe. Spodaj je, kaj to pomeni v praksi. To ni pravni nasvet; pri dvomih se obrni na pravnika ali na [Informacijskega pooblaščenca](https://www.ip-rs.si).

### 1. Beleži le, kar potrebuješ

Zapisuj podatke, ki jih res rabiš za delo s stranko (cilji, načrt, izvedba, opombe). Ne zapisuj več, kot je potrebno.

### 2. Zdravstveni podatki so posebna vrsta podatkov

Poškodbe, bolezni, zdravila, nosečnost in podobno so po 9. členu GDPR posebna vrsta osebnih podatkov. Zapisuj jih samo z izrecno privolitvijo stranke ali kadar jih stranka sama sporoči za namen vadbe in se s tem strinja; hrani jih čim krajši čas in jih posebej zavaruj.

### 3. Stranko obvesti

Pred beleženjem ji povej (13. člen GDPR), kdo je upravljavec (ti), kaj beležiš in zakaj, kako dolgo hraniš, komu daš podatke (praviloma nikomur) in kakšne so njene pravice. Primer besedila, ki ga prilagodi sebi:

> Za načrtovanje vadbe si beležim tvoje ime, cilje, opombe o treningih in, če mi jih zaupaš, podatke o poškodbah. Podatki so le na mojem telefonu, jih ne dajem drugim in jih hranim, dokler sodelujeva, in še do 1 leto po koncu. Kadar koli lahko zahtevaš vpogled, popravek ali izbris. Piši mi na (tvoj naslov).

### 4. Pravice stranke

* **Vpogled in prenos:** v meniju stranke (⋯) izberi »Izvozi zapise (besedilo)«. Dobiš navadno besedilno datoteko, ki je NI šifrirana: pošlji jo samo stranki, po varnem kanalu.
* **Izbris:** v meniju stranke izberi »Izbriši stranko«. Izbriše stranko in vse njene zapise s tega telefona. Varnostne kopije, ki si jih že shranil, ostanejo, kjer so; izbriši jih tudi tam.
* **Popravek:** popraviš zapis neposredno.

### 5. Varnost

* Telefon zaščiti z zaklepom in ga posodabljaj.
* Varnostna kopija je vedno šifrirana z geslom; geslo zapiši na papir, ne na isti telefon. Brez gesla kopije ni mogoče odpreti in gesla ni mogoče obnoviti.
* Izvoženih besedil ne puščaj v odložišču, v pošti ali v oblaku brez zaščite.
* Če telefon izgubiš ali ti ga ukradejo, so zapisi odvisni od zaklepa naprave.

### 6. Kršitev varnosti

Če izgubiš napravo ali kopijo s podatki strank in obstaja tveganje za njihove pravice (zlasti pri zdravstvenih podatkih), lahko to pomeni kršitev varstva osebnih podatkov. Po 33. členu GDPR jo je treba brez nepotrebnega odlašanja, če je mogoče v 72 urah, prijaviti Informacijskemu pooblaščencu, stranke pa obvestiti, če je tveganje visoko.

### 7. Rok hranjenja

Določi rok in ga spoštuj. Ko sodelovanje preneha in roka ni več, stranko izbriši.

## Brisanje vsega

V razdelku »Varnostna kopija« izberi ⋯ in »Izbriši vse podatke na tej napravi«. Aplikacija vpraša dvakrat. Lahko tudi v brskalniku počistiš podatke strani ali odstraniš nameščeno aplikacijo. Brez varnostne kopije podatkov nihče ne more vrniti.

## Povezave

Specifikacija in koda: [LibrePTNotes na GitHubu](https://github.com/stutek/LibrePTNotes).
