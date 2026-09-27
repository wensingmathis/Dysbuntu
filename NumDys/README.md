# NumDys

Une calculatrice scientifique et graphique inspirée de la **NumWorks**,
native pour Linux (testée pour **Debian**), avec la police
**OpenDyslexic** sur toute l'interface.

## Applications incluses

| Application  | Description |
|--------------|--------------|
| **Calculs**    | Calculatrice scientifique (sin, cos, tan, ln, log, √, puissance, π, e, Ans) avec historique des calculs |
| **Graphiques** | Traceur de courbes `y = f(x)`, avec zoom (+/−) et déplacement (flèches) |
| **Équations**  | Résolution d'équations du 1ᵉʳ degré (`ax + b = 0`) et du 2nd degré (`ax² + bx + c = 0`, avec discriminant et racines complexes) |
| **Suites**     | Suites définies par récurrence `u(n+1) = f(u, n)`, calcul des N premiers termes |
| **Réglages**   | Bascule Degrés / Radians pour toute l'application |

L'écran d'accueil affiche une grille d'icônes, comme sur une calculatrice
NumWorks, pour naviguer entre les applications.

## Installation sur Debian

```bash
sudo apt update
sudo apt install python3-gi gir1.2-gtk-3.0 fonts-opendyslexic
```

> Si `fonts-opendyslexic` n'existe pas dans vos dépôts (certaines
> versions de Debian ne l'incluent pas), installez la police
> manuellement :
>
> 1. Téléchargez-la depuis https://opendyslexic.org/
> 2. Copiez les fichiers `.otf` dans `~/.local/share/fonts/`
> 3. Lancez `fc-cache -f` pour rafraîchir le cache de polices

## Lancement

Depuis le dossier du projet :

```bash
python3 main.py
```

## Architecture du projet

```
numdys-project/
├── main.py                    # Fenêtre principale, barre supérieure, navigation
├── numdys/
│   ├── __init__.py
│   ├── safe_eval.py            # Évaluateur d'expressions sécurisé (ast, sans eval())
│   ├── style.py                 # CSS GTK — thème sombre + police OpenDyslexic
│   ├── state.py                  # État partagé (mode degrés/radians, dernier résultat)
│   ├── app_home.py               # Écran d'accueil (grille d'icônes)
│   ├── app_calculator.py         # Application Calculs
│   ├── app_graphing.py           # Application Graphiques
│   ├── app_equations.py          # Application Équations
│   ├── app_sequences.py          # Application Suites
│   └── app_settings.py           # Application Réglages
└── README.md
```

Cette architecture modulaire (une application = un fichier, un état
partagé injecté à chaque application) permet d'ajouter facilement de
nouvelles applications, comme le fait NumWorks avec ses "apps"
(Probabilités, Statistiques, Régression, Python...).

## Sécurité des calculs

Aucune expression saisie par l'utilisateur n'est jamais passée à
`eval()` ou `exec()`. Le module `safe_eval.py` analyse chaque
expression sous forme d'arbre syntaxique (module `ast` de Python) et
n'autorise que : nombres, opérateurs arithmétiques, quelques constantes
(`pi`, `e`) et une liste explicite de fonctions mathématiques (`sin`,
`cos`, `tan`, `sqrt`, `ln`, `log`, `exp`, `abs`, etc.).

## Limites connues / pistes d'évolution

- Pas encore d'application Statistiques, Probabilités ou Python (comme
  sur une vraie NumWorks) — l'architecture modulaire est prête à en
  accueillir.
- Le traceur de graphiques ne gère qu'une seule fonction `f(x)` à la
  fois.
- Testé avec la bibliothèque GTK3 standard de Debian ; non testé sur
  Wayland pur sans XWayland (devrait fonctionner nativement, GTK3
  supportant Wayland).

## Intégration dans le dépôt linux-pour-dys

Ce projet peut être ajouté comme un nouveau dossier
(`numdys/` ou `calculatrice-numworks-dys/`) dans le dépôt GitHub
`linux-pour-dys`.
