# Clavia 3.5.7

Jeu éducatif natif Linux pour apprendre à taper des mots, des phrases et des textes en AZERTY français. Clavia utilise Python, GTK4 et SQLite, fonctionne hors ligne et conserve les sauvegardes locales lors des mises à jour. Licence MIT.

## Nouveautés de la version 3.5.7

- Validation stricte des compteurs, des métriques et du volume pour rejeter les valeurs incohérentes ou non finies.
- Blocage des insertions groupées directement dans le tampon GTK, y compris le collage contextuel et le glisser-déposer.
- Écritures SQLite transactionnelles, erreurs de sauvegarde explicites et lecture groupée des meilleurs scores.
- Sons limités à une liste autorisée, nombre de lecteurs borné et processus audio récoltés à l'arrêt.
- Transitions d'exercice protégées contre les anciens événements GTK ; installation locale autonome après déplacement des sources.
- Ajout des fonds alternés et de `python3-gi-cairo` pour les graphiques GTK.
- Tests de durcissement et audit de sécurité ajoutés.

## Fonctionnalités conservées

- 36 niveaux répartis en six chapitres, avec progression, XP, scores, badges, objectifs et défi Sprint de 60 secondes.
- Interface Dark Slate avec thèmes sombre et clair mémorisés dans les préférences.
- Clavier virtuel AZERTY français amélioré, touches guidées et apostrophes droites et typographiques reconnues comme équivalentes.
- Douze sons locaux facultatifs pour les touches, boutons et récompenses. Les sons de frappe, de récompense et le volume se règlent dans les paramètres. La lecture utilise `paplay` lorsqu’il est disponible.
- Page Statistiques avec historique, records et graphique de vitesse, plus flamme de série quotidienne.
- Boutons Continuer et Sprint animés, et fonds visuels adaptés aux groupes de niveaux.
- Les paramètres d’accessibilité comprennent le texte agrandi, le clavier virtuel, les animations et OpenDyslexic si la police est installée.

## Installation

```bash
sudo apt install ./clavia_3.5.7_all.deb
clavia
```

Sur Debian, Ubuntu et Linux Mint, installer les dépendances système avec APT :

```bash
sudo apt update
sudo apt install python3 python3-gi python3-gi-cairo gir1.2-gtk-4.0 pulseaudio-utils
```

Le paquet déclare ces dépendances, dont `python3-gi-cairo` pour les graphiques GTK. Depuis les sources, lancer ensuite `python3 src/main.py`.

L'installation locale sans privilèges copie une installation autonome et ajoute un lanceur de menu :

```bash
sh ./install-local.sh
~/.local/bin/clavia
```

Pour reconstruire le paquet Debian avec `dpkg-deb` installé :

```bash
sh ./packaging/build-deb.sh
sudo apt install ./clavia_3.5.7_all.deb
```

## Tests

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
sh -n install-local.sh packaging/build-deb.sh
```

## Sécurité et performances

Clavia fonctionne hors ligne et ne contacte aucun service réseau. Les écritures SQLite sont transactionnelles ; les erreurs de sauvegarde sont signalées et les sauvegardes existantes ne sont ni supprimées ni réinitialisées lors d'une mise à jour. La base utilisateur reste dans `~/.local/share/jeu-clavier/progress.db`. Pour une mise à jour sensible, quitter Clavia et copier cette base avant l'installation.

Les entrées de score et les préférences sont validées, les requêtes SQLite sont paramétrées et les sons sont choisis dans une liste autorisée. Les processus audio sont bornés puis attendus à l'arrêt. La base demeure modifiable par son propriétaire : les scores locaux ne sont pas une preuve anti-triche inviolable. Les tests automatisés couvrent le stockage, le moteur, l'audio simulé et les fonctions de durcissement ; ils ne remplacent pas un essai de l'interface GTK4 sur une session Linux graphique.

Les ressources graphiques et les douze fichiers WAV historiques sont conservés. La notice `assets/sounds/README-LICENCES.txt` documente la confirmation des droits de redistribution des sons.

## Historique

Les fonctionnalités et instructions de Clavia 3.5.4 sont conservées dans ce README ; les changements documentés de cette version sont consignés dans [CHANGELOG.md](CHANGELOG.md). L'historique Git du dépôt reste la référence des commits antérieurs.
