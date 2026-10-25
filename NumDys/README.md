# NumDys

NumDys est un logiciel éducatif et accessible de calculatrice scientifique et graphique, inspiré de la **NumWorks** et conçu pour Linux. Il facilite l'apprentissage des mathématiques, notamment pour les personnes présentant des troubles dys. L'interface GTK 3 peut utiliser la police **OpenDyslexic** lorsqu'elle est installée.

L'écran d'accueil présente les applications sous forme de grille d'icônes, à la manière d'une calculatrice NumWorks. Le projet est organisé de façon modulaire : chaque application est séparée et partage un état commun, ce qui permet d'envisager l'ajout d'autres outils éducatifs (statistiques, probabilités ou Python).

## Fonctionnalités

| Module | Description |
|---|---|
| **Calculatrice scientifique** | Calculs avec sin, cos, tan, ln, log, racine carrée, puissances, π, e et Ans, avec historique. |
| **Graphiques mathématiques** | Tracé de `y = f(x)`, zoom avant/arrière et déplacement dans le graphique. |
| **Résolution d'équations** | Équations du premier degré (`ax + b = 0`) et du second degré (`ax² + bx + c = 0`), discriminant et racines complexes. |
| **Suites numériques** | Suites définies par récurrence `u(n+1) = f(u, n)` et calcul des premiers termes. |
| **Paramètres d'accessibilité** | Choix degrés/radians pour les fonctions trigonométriques et interface adaptée à OpenDyslexic si disponible. |

## Nouveautés — Version 0.2.0

- Évaluation des expressions mathématiques sécurisée par un analyseur AST et une liste blanche.
- Protection contre les calculs excessivement complexes grâce à des limites de taille, de profondeur, de nœuds et de valeurs.
- Moteur de calcul optimisé, avec compilation réutilisée pour les suites et les graphiques.
- Performances graphiques améliorées par la limitation et la préparation des échantillons.
- Meilleure gestion des erreurs mathématiques et des entrées invalides.
- Historique limité aux 100 dernières entrées pour maîtriser la mémoire.
- Code Python restructuré en modules plus faciles à maintenir et à tester.
- Ajout de tests automatisés pour le moteur mathématique et les modèles.
- Ajout d'un paquet Debian autonome, hors ligne après installation et sans téléchargement de code au démarrage.

Voir [CHANGELOG.md](CHANGELOG.md) pour l'historique des versions.

## Installation

Le paquet Debian convient à Ubuntu, Debian et Linux Mint. Il nécessite Python 3.10 ou plus, PyGObject et GTK 3. La police OpenDyslexic est facultative.

```bash
python3 --version
sudo apt update
sudo apt install python3 python3-gi gir1.2-gtk-3.0
```

Vérifiez que la version affichée par `python3 --version` est au moins 3.10. Le paquet Debian déclare aussi cette version minimale.

Installez ensuite le paquet fourni dans ce dossier :

```bash
sudo apt install ./numdys_0.2.0-1_all.deb
numdys
```

Si l'ancien paquet `dysbuntu-numdys-online` est installé, retirez-le avant la migration :

```bash
sudo apt remove dysbuntu-numdys-online
sudo apt install ./numdys_0.2.0-1_all.deb
```

Pour bénéficier de la police OpenDyslexic, installez `fonts-opendyslexic` si elle est disponible dans vos dépôts. Sinon, téléchargez-la depuis [opendyslexic.org](https://opendyslexic.org/), copiez les fichiers `.otf` dans `~/.local/share/fonts/` puis actualisez le cache avec `fc-cache -f`. Sans cette police, GTK utilise une police de remplacement.

Pour lancer les sources sans installer le paquet, depuis `NumDys/` :

```bash
python3 main.py
```

Sur Debian et ses dérivées, `/usr/bin/python3` donne généralement accès au paquet système PyGObject. Le paquet Debian déclare ses dépendances et installe la commande `numdys`.

## Tests

Depuis le dossier `NumDys/` :

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q main.py numdys
```

La construction locale du paquet nécessite `dpkg-deb` :

```bash
python3 packaging/build_deb.py
```

## Architecture du projet

```text
NumDys/
├── main.py
├── numdys/
│   ├── safe_eval.py       # Évaluation mathématique sécurisée
│   ├── math_models.py     # Modèles d'équations et de suites
│   ├── app_calculator.py
│   ├── app_graphing.py
│   ├── app_equations.py
│   ├── app_sequences.py
│   ├── app_home.py
│   ├── app_settings.py
│   ├── state.py
│   └── style.py
├── packaging/build_deb.py
├── tests/
└── README.md
```

## Sécurité des calculs

Les expressions saisies sont analysées avec le module Python `ast`, puis interprétées par une liste blanche fermée. Elles ne sont pas transmises à `eval()` ou `exec()` ; les imports, accès aux attributs et méthodes, et compréhensions ne sont pas autorisés. Des bornes limitent la taille des expressions, leur complexité, les exposants et les valeurs intermédiaires. Le traceur limite également le nombre d'échantillons et les suites le nombre d'itérations. Ces garde-fous réduisent les entrées pathologiques mais ne constituent pas une sandbox isolée du système.

## Limites connues et pistes d'évolution

- Les applications Statistiques, Probabilités et Python ne sont pas encore incluses ; l'architecture modulaire permet de les envisager.
- Le traceur de graphiques affiche une seule fonction `f(x)` à la fois.
- Les calculs utilisent des nombres flottants ; ils ne fournissent pas d'arithmétique symbolique ou de précision arbitraire.
- La fenêtre GTK n'a pas été validée sur toutes les versions de Debian, Ubuntu et Linux Mint ni sur toutes les configurations Wayland.

## Historique et intégration

NumDys est une calculatrice scientifique et graphique native Linux, inspirée de NumWorks et testée initialement sur Debian. Son architecture modulaire (une application par fichier et un état partagé) a été pensée pour accueillir des fonctions éducatives supplémentaires. Le projet est intégré au dépôt [Dysbuntu](https://github.com/wensingmathis/Dysbuntu), dans le dossier `NumDys/`.

## Crédits

Développé par **Mathis Wensing** dans le cadre du projet Dysbuntu. NumDys s'inspire de l'organisation en applications de la calculatrice NumWorks. La police OpenDyslexic est un projet distinct, disponible sur [opendyslexic.org](https://opendyslexic.org/).
