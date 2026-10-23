# Clavia 3.5.4

Jeu éducatif natif Linux pour apprendre la frappe AZERTY française. Clavia utilise Python, GTK4 et SQLite, fonctionne hors ligne et conserve les sauvegardes locales lors des mises à jour. Licence MIT.
## Nouveautés

- 36 niveaux répartis en six chapitres, avec progression, badges, objectifs et défi Sprint de 60 secondes.
- Interface Dark Slate avec thèmes sombre et clair mémorisés dans les préférences.
- Clavier virtuel AZERTY français amélioré, touches guidées et apostrophes droites et typographiques reconnues comme équivalentes.
- Douze sons locaux facultatifs pour les touches, boutons et récompenses. Les sons de frappe, de récompense et le volume se règlent dans les paramètres. La lecture utilise `paplay` lorsqu’il est disponible.
- Page Statistiques avec historique, records et graphique de vitesse, plus flamme de série quotidienne.
- Boutons Continuer et Sprint animés, et fonds visuels adaptés aux groupes de niveaux.
- Les paramètres d’accessibilité comprennent le texte agrandi, le clavier virtuel, les animations et OpenDyslexic si la police est installée.

## Installation

```bash
sudo apt install ./clavia_3.5.4_all.deb
clavia
```

Depuis les sources, installer GTK4/PyGObject puis lancer `python3 src/main.py`. Le script `./install-local.sh` ajoute une entrée de menu locale. Pour reconstruire le paquet : `./packaging/build-deb.sh`.

## Tests

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q src
```

La base SQLite utilisateur reste dans `~/.local/share/jeu-clavier/progress.db` et n’est pas supprimée ni réinitialisée par une mise à jour.
