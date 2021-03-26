# dvarapandita
* link zu Transliteration package pip: https://pypi.org/project/indic-transliteration/
* OCR: tesseract (tesseract-gui fuer graphische Anwendung; verschiedene Modelldaten sind im Internet zu finden (z.B. Sanskrit IAST) 
* OCR: Vielleicht spezifisch nach Sanskrit Devanagari Paket suchen? 

** Erster Schritt (Vladimir): TXT Dateien in data/ ablegen 
*** Vorformatierung ist wichtig: Eine Zeile nicht mehr als 150 Zeichen enthalten
*** 1. Alle Zeilenumbrueche loeschen 
*** 2. Nach jedem Danda/Punkt/Komma/Doppelpunkt neue Zeile einfuegen 
*** Englische Kommentare sollten geloescht werden
*** Kapitel-Aufteilung etc. am besten in getrennten Dateien machen! Z.B. kapitel01.txt, kapitel02.txt etc. 
*** Dateinamen: Keine Diakritika und keine Punktuation chap010
*** Alle Woerter, die nicht-alphabetische Zeichen enthalten (ausgenommen Punktuation am Ende) werden geschloescht, z.B. bh02_1
*** Wort = alles zwischen zwei Leerzeichen; Klammern, eckig sowohl wie rund, werden als nicht-alphabetisches Zeichen behandelt  

** Zweiter Schritt (Sebastian): TXT Dateien segmentieren/stemmen/ und in tsv-Ordner ablegen 

** Dritter Schritt (Sebastian): Vektorisieren + Indexing

** Vierter Schritt (Sebastian): Output-Dateien (Excel? TSV? Graphen fuer Gephi?) der Parallelen etc. erzeugen

** Fuenfter Schritt (Vladimir): Philologische Auswertung der Ergebnisse, Korrektur der Parameter, Wiederholung des Experimentes usw. 


