# Journal des modifications

## 0.1.0 — 2026-10-10 (première version, non publiée)
- Extension `.oxt` (Python-UNO) : correcteur `XProofreader` pour le français, appelant un serveur LanguageTool local.
- Menu « Dysbuntu » : vérifier la sélection, vérifier le document (revue guidée), démarrer/tester le serveur, options, règles ignorées, à propos.
- Catégories colorées, explications simples, suggestions en un clic, « ignorer » / « toujours ignorer cette règle ».
- Scripts d'installation (extension, LanguageTool avec consentement), désinstallation, lancement manuel du serveur.
- Tests : 70+ tests automatisés dont un test dans un vrai LibreOffice 24.2 (headless) avec un faux serveur LanguageTool.
- Non testé : vrai serveur LanguageTool, soulignement en direct dans l'interface graphique, Linux Mint.
