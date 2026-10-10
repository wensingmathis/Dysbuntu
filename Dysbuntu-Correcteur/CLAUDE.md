# CLAUDE.md — Dysbuntu Correcteur

Mémoire technique pour Claude Code. À lire au début de chaque session ; ne relire que les fichiers utiles à la tâche.

## Présentation
Extension LibreOffice Writer (`.oxt`) corrigeant orthographe, grammaire, accords et ponctuation du **français**, via un serveur **LanguageTool local**. Public : personnes dys (dyslexie, dysgraphie, dysorthographie). Principes : accessibilité, **confidentialité absolue** (rien ne sort de la machine, aucune télémétrie), logiciel libre, hors ligne. Ne remplace pas un professionnel de santé ou un accompagnement pédagogique.

## Architecture
```
Writer ──XProofreader──> DysbuntuProofreader.py ──> proofread.Proofreader ──HTTP 127.0.0.1──> LanguageTool (Java)
Menu Dysbuntu ──ProtocolHandler──> DysbuntuDispatch.py ──> review.ReviewSession + ui (dialogues UNO)
Job onFirstVisibleTask ──> DysbuntuStartupJob ──> server.ServerManager (démarre/arrête Java)
```
- Python-UNO, bibliothèque standard uniquement. Logique pure dans `extension/pythonpath/dysbuntu_correcteur/` (testable sans LibreOffice) ; le chargeur Python de LibreOffice ajoute `pythonpath/` à `sys.path`.
- Choix : service `XProofreader` (soulignement et menu contextuel natifs de Writer) plutôt que Java (fragile) ; moteur derrière `Proofreader` (extensible à d'autres langues/moteurs) ; serveur local sans `--public`.
- Positions : LibreOffice et LanguageTool comptent en **UTF-16** ; `goRight()` compte en points de code → conversions dans `textutil.py` / `uno_document.py`.

## Arborescence
- `extension/` : contenu du .oxt. `DysbuntuProofreader.py` (point d'entrée correcteur), `DysbuntuDispatch.py` (menu + job de démarrage), `registry/*.xcu` (déclarations : Linguistic, Addons=menu, ProtocolHandler, Jobs), `META-INF/manifest.xml`, `description.xml` (id `org.dysbuntu.correcteur`).
- `extension/pythonpath/dysbuntu_correcteur/` : `config.py` (réglages JSON, refuse tout hôte non local), `lt_client.py` (API /v2/check, sans proxy), `proofread.py` (filtres, cache, découpage), `categories.py` + `explain.py` (catégories, couleurs, phrases simples), `review.py` (revue guidée, adaptateur abstrait), `uno_document.py` (adaptateur Writer), `ui.py` (dialogues), `server.py` (processus Java), `core.py` (singleton), `paths.py`, `logutil.py`, `textutil.py`.
- `tests/` : tests unitaires + `test_lo_integration.py` (vrai LibreOffice headless) + `fake_languagetool.py` (faux serveur de test/démo).
- `scripts/` : `install.sh`, `install_languagetool.sh` (consentement), `start_server.sh`, `uninstall.sh`. `build.py` / `Makefile` : construction.
- Où ajouter : nouvelle catégorie → `categories.py` + `config.CATEGORY_KEYS` + `ui.build_options_dialog` ; nouvelle commande de menu → `registry/Addons.xcu` + `DysbuntuDispatch.dispatch` ; nouvelle langue → `Linguistic.xcu` + `proofread.supports_language` + `lt_client.language_code`.

## Installation et développement
- Dépendances : `libreoffice-writer libreoffice-script-provider-python python3-uno default-jre-headless` (Java ≥ 17 pour LanguageTool).
- `make build` → `dist/dysbuntu-correcteur-0.1.0.oxt` ; `make test` ; `make install` / `make uninstall` (LibreOffice fermé, **pas en root** : unopkg refuse) ; `scripts/install_languagetool.sh` ; `make demo-server` (faux serveur).
- Test headless : `python3 -m unittest tests.test_lo_integration -v` (installe le .oxt dans un profil temporaire ; en root il passe par `runuser -u nobody`).
- Pièges découverts : (1) `OpenOffice.org-minimal-version` accepté, `LibreOffice-minimal-version` refuse l'installation ; (2) `gotoStart()` d'un curseur de paragraphe va au début du **texte entier** → utiliser `createTextCursorByRange(para.getStart())` ; (3) remplacer par `setString()` au début d'une plage la fait rétrécir → insérer après puis supprimer l'ancien ; (4) énumérer une sélection renvoie des paragraphes ENTIERS → la sélection est traitée comme plages ; (5) `pkill -f` peut tuer son propre shell.

## Conventions
Python 3.8+, `from __future__ import annotations`, types, docstrings en français, noms anglais/français explicites. Aucune dépendance externe dans l'extension. Les composants UNO ne laissent jamais remonter d'exception vers Writer (journal + résultat vide). **Journaux : jamais de texte de document** (test automatisé). Aucune URL distante dans le code (test automatisé). Toute réponse du serveur est validée (`parse_matches`).

## État actuel (2026-10-10)
Terminé ET testé (73 tests, dont LibreOffice 24.2 réel en headless, avec FAUX LanguageTool) : enregistrement du correcteur pour fr-*, `doProofreading` (offsets UTF-16, suggestions, couleurs `LineColor`), menu et gestionnaire de commandes, revue guidée sur document/tableaux/sélection multi-paragraphes, construction des dialogues, config/vie privée, gestion du processus serveur (avec faux « java »), scripts d'installation (testés hors ligne avec archive factice).
**Jamais testé** : vrai LanguageTool (pas de réseau dans l'environnement de développement) ; soulignement en direct et menu contextuel dans l'interface graphique ; effet réel de `LineColor` ; clics dans les dialogues ; Linux Mint ; démarrage automatique réel de Java ; fusion avec le vérificateur orthographique de LibreOffice (doublons possibles).
Bugs/limites connus : conjugaison non distinguée (catégorie Grammaire) ; notes de bas de page/en-têtes non parcourus par la revue guidée ; premier démarrage de LanguageTool lent (les premières vérifications peuvent revenir vides, cache non rempli dans ce cas).
**Prochaine étape recommandée** : test manuel sur Ubuntu/Mint avec le vrai LanguageTool (`scripts/install.sh --with-languagetool`), vérifier soulignement/menu contextuel, puis corriger selon les retours ; ensuite choisir la licence, ajouter captures et `.github` CI.

## Règles pour Claude Code
- Lire ce fichier d'abord ; consulter seulement les fichiers pertinents.
- Mettre à jour ce fichier après tout changement d'architecture, dépendance, commande ou fonctionnalité, et l'état d'avancement après chaque étape.
- Ne jamais déclarer une fonctionnalité terminée sans test ; distinguer « testé avec faux serveur » et « testé avec vrai LanguageTool ».
- Pas de code source complet, mot de passe ou jeton dans ce fichier. Remplacer les informations périmées au lieu d'accumuler.
