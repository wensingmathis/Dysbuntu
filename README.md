# Dysbuntu

<p align="center">
  <img src="logo Dysbuntu.png" alt="Logo Dysbuntu" width="260" style="background-color:white; padding:18px; border-radius:12px;">
</p>

> Logo Dysbuntu © 2026 Mathis Wensing. Tous droits réservés.  
> Le code source et les contenus du dépôt sont distribués sous licence GPL-3.0, sauf indication contraire.

Dysbuntu est un projet open source d'accessibilité informatique basé sur Ubuntu, conçu pour faciliter l'usage de Linux par les personnes dyslexiques, dysgraphiques ou dysorthographiques.

Le projet vise à rendre l'informatique plus lisible, plus simple et plus inclusive, tout en restant libre, privé et personnalisable.

---

## Droits d'auteur et licence

Copyright © 2026 Mathis Wensing.

Sauf indication contraire, le code source et les contenus originaux de Dysbuntu sont distribués selon les conditions de la GNU General Public License v3.0 (GPL-3.0). Consultez [LICENSE](LICENSE).

Les composants et ressources provenant de tiers restent soumis à leurs propres licences et droits d'auteur.

---

## Objectif du projet

Dysbuntu a pour objectif de proposer un environnement Linux :

- simple
- accessible
- personnalisable
- respectueux de la vie privée
- orienté vers la souveraineté numérique
- compatible avec l'usage quotidien du bureau et des outils éducatifs

Le projet s'appuie sur Ubuntu et intègre des outils spécialement pensés pour réduire les difficultés de lecture, d'écriture et de compréhension des interfaces numériques.

---

## Police d'écriture

Dysbuntu utilise la police OpenDyslexic pour l'interface et les textes.

Cette police a été choisie pour améliorer la lisibilité pour certaines personnes dyslexiques, notamment grâce à la forme spéciale des lettres.

---

## Structure du dépôt

```text
Dysbuntu/
├── .github/
├── .gitignore
├── LICENSE
├── README.md
├── logo Dysbuntu.png
├──  images accueil.png
├── Vocalis/
│   ├── README.md
│   ├── app.py
│   ├── manager.py
│   ├── main.py
│   ├── install.sh
│   ├── diagnostic_piper.py
│   ├── __init__.py
│   ├── Vocalis.jpeg
│   ├── dysbuntu-vocalis-online_0.1.0-1_all.deb
│   ├── tts/
│   └── ui/
├── Dysbuntu-Correcteur/
│   ├── README.md
│   ├── CHANGELOG.md
│   ├── CLAUDE.md
│   ├── Makefile
│   ├── build.py
│   ├── dysbuntu-correcteur-0.1.0.png
│   ├── docs/
│   ├── extension/
│   ├── scripts/
│   └── tests/
├── NumDys/
│   ├── README.md
│   ├── main.py
│   ├── dysbuntu-numdys-online_0.1.0-1_all.deb
│   └── numdys/
├── Clavia/
│   ├── README.md
│   ├── LICENSE
│   ├── requirements.txt
│   ├── install-local.sh
│   ├── clavia_3.5.4_all.deb
│   ├── assets/
│   ├── packaging/
│   ├── src/
│   └── tests/
└──
```

---

## Logiciels et outils inclus

### Vocalis

<p>
  <img src="Vocalis/Vocalis.jpeg" alt="Logo de Vocalis" width="120" style="background-color:white; padding:12px; border-radius:10px;">
</p>

Application de lecture de texte créée pour Dysbuntu.

- Synthèse vocale avec Piper
- eSpeak NG comme solution de secours
- Fonctionnement local
- Lecture de textes à voix haute
- Interface simple et accessible

Code source : dossier `Vocalis/` dans ce dépôt.

### Dysbuntu Correcteur

<p>
  <img src="Dysbuntu-Correcteur/dysbuntu-correcteur-0.1.0.png" alt="Logo Dysbuntu Correcteur" width="220" style="background-color:white; padding:18px; border-radius:12px;">
</p>

Extension LibreOffice Writer (`.oxt`) qui corrige l'orthographe, la grammaire, les accords et la ponctuation du français.

- Soulignement en direct dans Writer selon le type d'erreur
- Menu Dysbuntu intégré : vérification de la sélection ou du document complet
- Revue guidée interactive : corriger en un clic, ignorer ou désactiver une règle
- Explications en phrases simples
- Personnalisation des types d'erreurs et taille du texte réglable
- Serveur LanguageTool local : tout fonctionne sans internet
- Rien n'est modifié sans votre clic

Code source : dossier `Dysbuntu-Correcteur/` dans ce dépôt.

### NumDys

<p align="center">
  <em>Calculatrice scientifique et graphique pour Linux</em>
</p>

Calculatrice scientifique et graphique native pour Linux, inspirée par la NumWorks, avec la police OpenDyslexic.

Applications incluses :

| Application | Description |
|-------------|-------------|
| Calculs | Calculatrice scientifique (sin, cos, tan, ln, log, √, puissance, π, e, Ans) avec historique |
| Graphiques | Traceur de courbes `y = f(x)`, avec zoom et déplacement |
| Équations | Résolution du 1er et 2nd degré avec discriminant et racines complexes |
| Suites | Suites définies par récurrence `u(n+1) = f(u, n)` |
| Réglages | Bascule Degrés / Radians pour l'application |

Interface intuitive avec grille d'icônes et navigation fluide.

Code source : dossier `NumDys/` dans ce dépôt.

### Clavia

Jeu éducatif natif Linux pour apprendre la dactylographie en français, avec une interface GTK4 et une sauvegarde locale SQLite.

- 36 niveaux répartis en six chapitres, défi Sprint, statistiques, badges et série quotidienne
- Thèmes Dark Slate clair et sombre, clavier virtuel AZERTY guidé et apostrophes corrigées
- 12 sons facultatifs, boutons animés, flamme de série et fonds par niveau
- Fonctionnement hors ligne, progression SQLite conservée lors des mises à jour
- Interface adaptée à OpenDyslexic lorsqu'elle est installée
- Version actuelle : 3.5.4
- Sauvegardes conservées lors des mises à jour

Code source : dossier `Clavia/` dans ce dépôt. Clavia est distribué sous licence MIT (voir `Clavia/LICENSE`).

---

## Outils et projets tiers intégrés

### LibreOffice

Suite bureautique libre.

Projet : https://github.com/LibreOffice/core

### ONLYOFFICE

Suite bureautique utilisée pour les documents.

Projet : https://github.com/ONLYOFFICE

### Mullvad Browser

Navigateur basé sur Firefox, conçu pour protéger la vie privée et limiter le pistage en ligne.

GitHub : https://github.com/mullvad/mullvad-browser

### Stirling PDF

Outil libre permettant de manipuler et modifier des fichiers PDF.

Projet : https://github.com/Stirling-Tools/Stirling-PDF

### Piper

Moteur de synthèse vocale utilisé par Vocalis.

Projet : https://github.com/rhasspy/piper

### eSpeak NG

Moteur de synthèse vocale utilisé comme solution de secours dans Vocalis.

Projet : https://github.com/espeak-ng/espeak-ng

### LanguageTool

Moteur de correction orthographique et grammaticale utilisé par Dysbuntu Correcteur.

Projet : https://github.com/languagetoolorg/languagetool

---

## Technologies

- Ubuntu
- Linux
- Python
- Tkinter
- GTK3
- GTK4
- SQLite
- Piper
- eSpeak NG
- LanguageTool
- OpenDyslexic
- LibreOffice

---

## Accessibilité

Dysbuntu est pensé pour faciliter l'utilisation d'un ordinateur par les personnes ayant des difficultés de lecture, d'écriture ou de compréhension des interfaces numériques.

Le projet reste ouvert à tous et peut être utilisé comme une distribution Linux classique.

---

## Philosophie du projet

Dysbuntu est un projet personnel et open source qui cherche à créer un environnement Linux :

- simple
- accessible
- libre
- respectueux de la vie privée
- personnalisable
- basé sur la souveraineté numérique

Le but est de créer un système adapté aux besoins des utilisateurs sans dépendre uniquement de solutions propriétaires.

---

## Nouveautés récentes

- Clavia est passé en version 3.5.4 : 36 niveaux, thèmes clair/sombre, clavier AZERTY amélioré, 12 sons facultatifs, statistiques, flamme, boutons animés et fonds par niveau. Les sauvegardes sont conservées.
- Le dépôt est structuré autour de plusieurs modules distincts : Vocalis, Dysbuntu Correcteur, NumDys et Clavia.
- Le projet s'appuie désormais sur une logique plus claire de modules indépendants, chacun avec son propre README, ses dépendances et ses outils.
- Les outils sont pensés pour être utilisables hors ligne, sans compte, sans publicité, et avec un minimum de dépendances externes.

---

## À propos de Dysbuntu

Dysbuntu n'est pas seulement une distribution Linux : c'est un ensemble d'outils, de logiciels et de bonnes pratiques orientés vers l'accessibilité numérique.

L'objectif est de proposer un environnement plus agréable, plus lisible et plus facile à utiliser pour les personnes qui rencontrent des difficultés dans l'usage quotidien du numérique.

---

## Liens utiles

- Licence : [LICENSE](LICENSE)
- Dépôt GitHub : https://github.com/wensingmathis/Dysbuntu
- Vocalis : `Vocalis/`
- Dysbuntu Correcteur : `Dysbuntu-Correcteur/`
- NumDys : `NumDys/`
- Clavia : `Clavia/`
