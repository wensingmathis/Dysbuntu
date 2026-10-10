# Dysbuntu Correcteur

Extension **LibreOffice Writer** (`.oxt`) qui corrige l'orthographe, la grammaire, les accords et la ponctuation du **français**, en s'appuyant sur un serveur **LanguageTool local** : tout fonctionne hors ligne, sans télémétrie. Elle fait partie du projet Dysbuntu (accessibilité numérique pour les personnes dyslexiques, dysgraphiques et dysorthographiques).

> Cet outil aide à relire. Il ne remplace ni une relecture attentive, ni un accompagnement pédagogique ou médical. Une suggestion peut être fausse : vérifiez-la.

## Ce que fait l'extension
- **Soulignement en direct** dans Writer (couleur selon le type d'erreur), suggestions dans le menu contextuel.
- **Menu Dysbuntu** : *Vérifier la sélection*, *Vérifier le document* (revue guidée, une erreur à la fois : corriger en un clic, ignorer, toujours ignorer la règle), *Démarrer / tester le serveur*, *Options*, *Réactiver les règles ignorées*, *À propos*.
- Explications en phrases simples ; types d'erreurs désactivables ; taille du texte des fenêtres réglable.
- Rien n'est modifié sans votre clic.

## Installation (Ubuntu / Linux Mint)
```bash
git clone <ce dépôt> && cd dysbuntu-correcteur
scripts/install.sh --with-languagetool   # apt (sudo), extension, puis LanguageTool (demande votre accord)
```
Ou pas à pas :
```bash
sudo apt install libreoffice-writer libreoffice-script-provider-python python3-uno default-jre-headless unzip curl
make install                       # construit et installe l'extension (LibreOffice fermé)
scripts/install_languagetool.sh    # télécharge LanguageTool (une seule fois, avec accord)
```
Ouvrez Writer : le menu **Dysbuntu** apparaît. Le serveur démarre tout seul (réglable dans *Options*). À la main : `scripts/start_server.sh`.

Pour que le soulignement en direct fonctionne : *Outils > Options > Paramètres linguistiques > Outils linguistiques > Modifier* : « Dysbuntu Correcteur » coché, et *Vérification automatique de l'orthographe* activée. La langue du texte doit être le français (*Outils > Langue > Pour tout le texte*).

## Désinstallation
`scripts/uninstall.sh` (ajoutez `--purge` pour supprimer réglages, journaux et LanguageTool).

## Développement
```bash
make build     # dist/dysbuntu-correcteur-0.1.0.oxt
make test      # tests unitaires + test dans un vrai LibreOffice (headless) avec un faux LanguageTool
make demo-server   # FAUX serveur de démonstration (quelques règles) sur le port 8081
```
Voir `CLAUDE.md` (architecture, conventions, état d'avancement) et `docs/CONFIDENTIALITE.md`.

## Limites connues
- Conjugaison et accords : LanguageTool les classe dans « Grammaire » ; pas de catégorie séparée.
- Revue guidée : texte des paragraphes et tableaux simples ; notes de bas de page, en-têtes, champs non parcourus.
- Français uniquement dans cette version.
