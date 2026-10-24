# Changelog

Les changements notables de Vocalis sont consignés ici. Les versions décrivent le code du projet; les validations listées ne valent pas certification de sécurité ou compatibilité universelle.

## [0.2.0] - 2026-10-24

### Ajouté
- Validation centralisée des textes et réglages, erreurs explicites et tests automatisés.
- Gestion des sous-processus avec annulation et délais maximaux.
- Transmission des événements à Tkinter par une file consommée dans le thread graphique.
- Traitement WAV par blocs, contrôle de la sortie, fichiers temporaires privés et export atomique.
- Script de construction Debian contenant les sources applicatives et le logo original.

### Modifié
- Organisation et typage des modules Python; Piper devient facultatif et les moteurs détectés localement sont utilisés.
- Aucun téléchargement de code au démarrage. Les modèles Piper restent installés manuellement.
- README complété avec installation, utilisation, moteurs, sécurité, liens et limites connues.

### Vérifié
- Compilation des modules Python réussie.
- 13 tests automatisés réussis le 2026-10-24. Les tests de moteurs et d'export s'appuient sur des exécutables factices; aucune sortie audio réelle n'a été testée.
- Empreinte du logo `Vocalis.jpeg` identique entre la branche `main` avant intégration et l'archive de travail.
- Inspection des sources: pas d'appel réseau ni de téléchargement de code dans les modules applicatifs et scripts d'installation examinés.

### Non vérifié / limites
- Le paquet `.deb` n'a pas été construit ou installé: `dpkg-deb` n'est pas disponible dans l'environnement.
- Interface graphique, sortie audio réelle Piper/eSpeak NG, installation sur une machine Debian/Ubuntu et performances mémoire n'ont pas été testées ici.
- Le contrôle de taille du WAV intervient après génération et ne plafonne pas la consommation disque durant celle-ci.
- Les moteurs, modèles ONNX et bibliothèques natives tiers ne sont pas audités ni isolés par une sandbox fournie par Vocalis.

## [0.1.0] - Version historique

- Lecture de texte à voix haute sous Linux.
- Piper présenté comme moteur principal, eSpeak NG comme solution de secours et voix française `fr_FR-siwis-medium`.
- Fonctionnement local/hors ligne, enregistrement WAV et possibilité d'arrêter la lecture.
- Installation des moteurs et de la voix décrite dans le README historique.
