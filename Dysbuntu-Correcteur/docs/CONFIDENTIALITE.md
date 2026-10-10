# Confidentialité, sécurité et dépendances

## Principes
- **Aucun texte n'est envoyé sur Internet.** Le texte part uniquement vers `127.0.0.1` (votre machine).
- **Aucune télémétrie, aucune statistique.** Aucune bibliothèque de collecte n'est utilisée (un test automatisé le vérifie).
- **Aucun document conservé.** Le texte n'est gardé qu'en mémoire (petit cache de 256 paragraphes, vidé à la fermeture de LibreOffice) ; il n'est jamais écrit sur disque ni dans les journaux.
- Le serveur refuse tout autre hôte que `127.0.0.1`, `localhost`, `::1` (code et fichier de réglages), et le client ignore les variables de proxy.

## Connexions réseau (liste complète)
| Quand | Vers où | Pourquoi |
|---|---|---|
| Chaque vérification | `http://127.0.0.1:<port>/v2/check` | Envoyer le paragraphe au serveur local |
| Test de disponibilité | `http://127.0.0.1:<port>/v2/languages` | Savoir si le serveur répond |
| `scripts/install_languagetool.sh` (une fois, avec votre accord) | `https://languagetool.org/download/` | Télécharger LanguageTool |

## Fichiers écrits
- `~/.config/dysbuntu-correcteur/config.json` : réglages et règles ignorées.
- `~/.local/state/dysbuntu-correcteur/` : journaux (sans texte de document), journal du serveur.
- `~/.local/share/dysbuntu-correcteur/languagetool/` : LanguageTool.
`scripts/uninstall.sh --purge` supprime tout.

## Permissions
L'extension lance un processus Java (le serveur) en tant qu'utilisateur courant, sans droits supplémentaires, sans option `--public` (le serveur n'écoute pas le réseau).

## Dépendances et licences (à revérifier avant publication)
| Composant | Rôle | Licence indiquée par le projet |
|---|---|---|
| LibreOffice, API UNO | Hôte de l'extension | MPL 2.0 |
| Python 3 (fourni avec LibreOffice / python3-uno) | Langage | PSF |
| LanguageTool | Moteur de correction (téléchargé séparément, non redistribué ici) | LGPL 2.1 |
| OpenJDK / Java ≥ 17 | Exécute LanguageTool | GPL v2 + exception classpath |
Le code de l'extension n'utilise que la bibliothèque standard Python.
La licence du code de Dysbuntu Correcteur reste à choisir par l'auteur avant publication.
