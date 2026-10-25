# Historique des versions

## 0.2.0 - 2026-10-25

- Sécurisation de l'évaluation des expressions par AST et liste blanche, avec des limites contre les calculs excessivement complexes.
- Optimisation du moteur de calcul, notamment par compilation réutilisée dans les suites et les graphiques.
- Amélioration des performances du traceur et limitation des échantillons.
- Meilleure gestion des erreurs et validation des valeurs numériques.
- Limitation de l'historique de la calculatrice aux 100 dernières entrées.
- Restructuration du code Python en modules maintenables et ajout de tests automatisés.
- Ajout d'un paquet Debian autonome qui ne télécharge pas de code au démarrage.
- Conservation des modules historiques : calculs, graphiques, équations, suites et réglages degrés/radians.

## 0.1.0

- Première version documentée de la calculatrice scientifique et graphique GTK 3 pour Linux.
- Ajout des modules de calcul, de tracé de courbes, de résolution d'équations, de suites récurrentes et de réglages degrés/radians.
- Interface inspirée de NumWorks et prise en charge de la police OpenDyslexic lorsqu'elle est installée.