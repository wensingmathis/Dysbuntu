# Clavia 2.1 — Dark Minimal / Slate

Jeu éducatif **natif Linux** pour apprendre la dactylographie en français. Développé avec Python 3, GTK4 / PyGObject et SQLite, **sans connexion Internet**, sans compte, sans publicité et sans télémétrie. Licence MIT.

## Refonte graphique Dark Slate

- Palette : fond `#1E1E24`, cartes `#25252B`, texte `#D1D0C5`, texte en attente `#646669`, ambre `#E2B714`, erreurs `#CA4754`.
- Aucun gradient, néon, glassmorphism, effets 3D ou grosses bordures arrondies. Rayons de 6 à 8 px.
- Interface : Inter (ou police sans-serif système) ; saisie et statistiques : JetBrains Mono (ou monospace système).
- Zone de frappe sans navigation latérale : chronomètre démarré à la première touche, précision, vitesse et score visibles en haut.
- Le texte reste central, avec caractères corrigés en blanc cassé, erreurs en rouge, caractères restants en gris et position en ambre.
- Clavier AZERTY interactif : prochaine touche et frappe mises en évidence par une transition de 120 ms (désactivable).
- Graphique de progression simple sur les 20 derniers exercices.
- Badge flamme vectoriel mat et autres récompenses discrètes.
- Réglages : taille du texte, clavier virtuel, animations, police OpenDyslexic si installée.

## Gameplay

18 leçons progressives : **6 de mots, 6 de phrases et 6 de textes**, défi de 60 secondes, chrono, XP, scores, records, niveaux, badges et série quotidienne de jours. Les erreurs de frappe restent corrigeables avec Retour arrière. Les données sont enregistrées localement dans SQLite.

## Installation sur Linux Mint, Ubuntu et Debian

### Paquet Debian (recommandé)

```bash
sudo apt install ./clavia_2.1.0_all.deb
clavia
```

Le paquet installe le jeu et son entrée dans le menu des applications.

### Depuis le code source

```bash
sudo apt install python3-gi gir1.2-gtk-4.0
/usr/bin/python3 src/main.py
```

Pour une entrée de menu sans paquet Debian : `./install-local.sh`.

### Police OpenDyslexic (facultative)

Installe la police OpenDyslexic depuis ton gestionnaire de polices, puis relance Clavia : l'option apparaît dans **Paramètres** dès que `fc-list` la détecte. Activer la police la fait utiliser aussi bien par les menus que par le texte à recopier et la zone de saisie.

## Construire le paquet

```bash
./packaging/build-deb.sh
```

## Respect des sauvegardes

La base SQLite est conservée dans `~/.local/share/jeu-clavier/progress.db`. Les scores et préférences des versions précédentes sont conservés. Une mise à jour du paquet n'efface pas ce fichier utilisateur.

## Tests

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q src
```

## Code

- `src/main.py` : pages GTK4, clavier virtuel, dessin vectoriel de la flamme et du graphique.
- `src/engine.py` : calculs, couleurs des erreurs, chronomètre, XP et statistiques.
- `src/storage.py` : sauvegarde locale SQLite, historique des résultats.
- `src/content.py` : leçons françaises.
- `assets/style.css` : charte graphique Dark Slate et prise en charge OpenDyslexic.
- `assets/clavia.svg` : nouvelle icône vectorielle.
- `packaging/` : construction `.deb` et raccourci Linux.
- `tests/` : tests du moteur.

Le thème Dark Slate est volontairement unique : même si l'utilisateur avait sélectionné un thème clair dans une ancienne version, Clavia utilise désormais la palette sombre définie ici.

> Vérification : tests automatisés du moteur et compilation Python. Le rendu GTK réel doit être validé sur un bureau Linux avec GTK4 installé.
