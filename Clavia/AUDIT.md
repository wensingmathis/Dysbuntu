# Clavia — audit du code 3.5.6 et correctifs 3.5.7

## Périmètre

Code Python (`main.py`, `engine.py`, `storage.py`, `audio.py`, `content.py`), tests, installation locale, construction Debian et analyse des ressources. Application GTK4 hors ligne, comptes locaux ; aucune API HTTP, aucune donnée bancaire, aucun service distant.

## Sécurité

| Constat original | Risque | Correctif 3.5.7 / limite |
| --- | --- | --- |
| `main.py:on_key_pressed` ne bloque que Ctrl+V | Contournement des scores par collage contextuel/DnD/Shift+Insert | Rejet des insertions de longueur différente de 1 dans `Gtk.TextBuffer::insert-text`. Un logiciel local ne peut empêcher l'édition externe de SQLite. |
| `int(db.preference('sound_volume'))` sans validation | Exception au démarrage si valeur malformée | Fonction `safe_volume()` et tests. |
| Requêtes et modifications DB non protégées en cas de disque plein ou verrouillé | Crash ou sessions non enregistrées | `StorageError`, transactions et indication explicite d'échec à la fin d'une leçon. Les autres lectures doivent encore être testées en panne réelle. |
| `audio.play(name)` construit un chemin depuis `name` | Risque si noms deviennent externes | Liste blanche des noms WAV connus, commande exécutée sans shell. |
| `audio.close()` appelle `terminate()` sans attente | Processus fils non récoltés immédiatement | `wait(timeout)` et `kill()` si nécessaire. |
| Métriques acceptant `NaN`, négatifs, incohérences | Scores et graphes erronés | Validation `compute_metrics()` et `Storage.save()`. |
| `install-local.sh` incorpore un chemin source dans du shell généré | Installation fragile ou cassée après déplacement de sources | Copie autonome à `~/.local/share/clavia`; wrapper n'incorpore aucun chemin externe. |
| `home()` exécute 36 requêtes pour afficher les meilleurs scores | Coût SQLite répétitif | Nouvelle lecture groupée `best_by_lesson()`. |
| Ancien `idle_add(next_step, stage)` sans jeton de session | Événement GTK tardif potentiellement appliqué au mauvais exercice | Jeton de génération `exercise_token`. |

### Absences de risques observées

Les requêtes utilisent `?` (requêtes préparées) plutôt qu'une interpolation SQL ; `subprocess.Popen` utilise une liste d'arguments et pas `shell=True` ; `rich_target` échappe les caractères spéciaux pour Pango ; aucun serveur, réseau, authentification distante ou secrets intégrés n'a été identifié. Cela n'est **pas** une preuve d'absence universelle de vulnérabilités.

### Points qui demandent une validation indépendante

- UI GTK4, méthodes de saisie IME/accessibilité, événements clavier et animations sur Linux Mint.
- La notice suivie dans le dépôt confirme les droits de redistribution des douze sons ; les empreintes SHA-256 de l'archive 3.5.7 correspondent exactement aux WAV déjà publiés. Toute ressource audio nouvelle ou remplacée doit faire l'objet d'une confirmation distincte avant publication.
- Tests manuels de perte d'accès disque et de mise à jour depuis une installation antérieure.
- Authentification et signatures de paquets/release GitHub si distribution publique.

## Qualité / performances

`main.py` reste un module important de plus de 1 200 lignes. Une séparation ultérieure en composants de vue serait bénéfique, mais une réécriture intégrale de GTK sans test de rendu augmenterait le risque de régression. Les opérations de mise en forme de texte et de clavier sont linéaires dans la longueur du prompt/de la liste de touches et restent très petites pour le contenu fourni. La sauvegarde (SQLite) et la fréquence d'actualisation de 130 ms sont plus pertinentes à surveiller que ces boucles.

## Validation

La suite de tests standard-library est la preuve automatisée principale. La construction du paquet doit être répétée avec `dpkg-deb` dans un environnement compatible ; l'environnement actuel ne possède pas cet outil ni PyGObject/GTK4, donc ni le paquet 3.5.7 ni le démarrage graphique ne sont validés ici. Le champ Maintainer utilise le nom du titulaire du dépôt, sans adresse électronique inventée.
