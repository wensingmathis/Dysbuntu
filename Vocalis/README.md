# Vocalis

<p>
  <img src="Vocalis.jpeg" alt="Logo original de Vocalis" width="120">
</p>

Vocalis est une application Linux de synthèse vocale locale. Elle permet de faire lire un texte à voix haute et de l'enregistrer en WAV. Elle a été conçue pour faciliter l'accès à la lecture aux personnes dyslexiques, dysorthographiques ou rencontrant des difficultés de lecture.

Le texte et les fichiers audio sont traités sur l'ordinateur. Vocalis fait partie de Linux pour Dys, un projet qui vise à rendre l'environnement Linux plus simple et accessible aux personnes rencontrant des difficultés avec la lecture et l'écriture. Il privilégie les logiciels libres, la souveraineté numérique, la confidentialité et les outils locaux.

## Fonctionnalités

- Lecture à voix haute d'un texte saisi ou collé.
- Sélection des voix disponibles, avec filtre pour les voix françaises.
- Réglages de vitesse et de volume; réglage de hauteur lorsque le moteur le permet.
- Arrêt d'une lecture ou d'un enregistrement en cours.
- Export WAV et effacement rapide du texte.
- Utilisation hors ligne après installation des moteurs et des voix nécessaires.
- Moteurs locaux Piper et eSpeak NG; Piper est facultatif.

## Nouveautés de la version 0.2.0

- Validation des textes et des réglages, limites d'entrée et erreurs explicites.
- Gestion des sous-processus avec annulation et délais maximaux; les tests couvrent ces comportements avec des processus simulés.
- Interface Tkinter alimentée par une file d'événements, les mises à jour graphiques restant sur le thread principal. L'interface n'a pas été testée ici sur un bureau Linux réel.
- Traitement du volume WAV par blocs et vérification du fichier exporté; ces opérations ont des tests automatisés.
- Export vers un fichier temporaire privé puis remplacement atomique du fichier choisi, testé avec un moteur simulé.
- Aucun téléchargement de code au démarrage. Les voix Piper restent installées séparément par l'utilisateur.
- Script de construction d'un paquet Debian contenant le code applicatif et le logo. Le paquet n'a pas été construit ni installé dans l'environnement de vérification décrit ci-dessous.
- Sources réorganisées, typées et documentées, avec 13 tests automatisés sans accès réseau ni moteur vocal réel.

## Installation

### Debian, Ubuntu et Linux Mint

Les dépendances système principales sont Python 3.10 ou supérieur, Tkinter, eSpeak NG et un lecteur audio. Le script installe les paquets Debian nécessaires :

```bash
cd Vocalis
bash install.sh
python3 main.py
```

L'installation équivalente sans script est :

```bash
sudo apt update
sudo apt install -y python3 python3-tk espeak-ng alsa-utils
python3 main.py
```

### Ajouter Piper et une voix française

Piper est facultatif. Installez-le avec `pipx` :

```bash
sudo apt install -y pipx
pipx install piper-tts
pipx ensurepath
```

Fermez puis rouvrez la session du terminal si le programme `piper` n'est pas trouvé. Placez les fichiers du modèle et de sa configuration dans `~/piper-voices` :

```bash
mkdir -p ~/piper-voices
cd ~/piper-voices
wget -O fr_FR-siwis-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx?download=true"
wget -O fr_FR-siwis-medium.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx.json?download=true"
ls -lh ~/piper-voices/
```

Ces téléchargements sont manuels et concernent les fichiers de voix, pas du code lancé par Vocalis. Vérifiez leur provenance et leur intégrité. Vocalis recherche les modèles installés localement; il ne télécharge ni modèle ni code au démarrage. Piper utilise un lecteur WAV disponible sur le système (`paplay`, `aplay`, `ffplay` ou `play`).

### Construire le paquet Debian

Depuis le dossier `Vocalis/`, avec `dpkg-deb` installé :

```bash
./packaging/build-deb.sh
sudo apt install ../dysbuntu-vocalis_0.2.0-1_all.deb
vocalis
```

Le paquet embarque les sources applicatives et le logo. APT doit toujours pouvoir installer les dépendances système indiquées par le paquet. La construction et l'installation de ce `.deb` n'ont pas été validées dans l'environnement de publication actuel.

Après installation du paquet Debian, Vocalis peut également être lancé depuis le menu des applications.

## Utilisation

1. Lancez Vocalis avec `python3 main.py` ou, après installation du paquet Debian, avec `vocalis`.
2. Choisissez une voix. Le filtre « Voix françaises » est activé par défaut.
3. Saisissez ou collez le texte, puis réglez la vitesse, le volume et, si disponible, la hauteur.
4. Cliquez sur « Lire » pour écouter, sur « Arrêter » pour interrompre, ou sur « Enregistrer WAV » pour choisir un fichier de destination.
5. Utilisez « Effacer » pour vider la zone de texte.

Pour diagnostiquer la disponibilité de Piper et de ses modèles :

```bash
python3 diagnostic_piper.py
```

Les chemins de voix affichés dans le diagnostic dépendent du compte utilisateur et des modèles installés; l'ancien exemple `/home/mathis/...` n'est donc pas un chemin universel.

## Moteurs vocaux

### Piper

Piper fournit des voix installées séparément, dont la voix française `fr_FR-siwis-medium`. Vocalis ne récupère pas les modèles automatiquement. Le traitement de la sortie WAV et sa lecture utilisent les outils audio locaux disponibles.

### eSpeak NG

eSpeak NG fournit un moteur local et des voix système. Il est installé par le script et le paquet Debian; Piper peut être ajouté en complément. Les voix proposées dépendent des moteurs présents sur la machine.

## Sécurité et confidentialité

- Le texte est transmis au moteur par l'entrée standard, pas dans les arguments de commande; les processus sont lancés sans shell.
- La saisie est limitée à 5 000 caractères. Les sous-processus disposent de délais maximaux et peuvent être annulés.
- Les WAV temporaires sont privés; l'export vérifie le fichier et remplace la destination de façon atomique. La limite de taille WAV est contrôlée après génération: elle ne garantit pas un quota disque pendant la synthèse.
- Le code applicatif ne télécharge pas de code et n'envoie pas le texte à un serveur Vocalis. Les téléchargements facultatifs de modèles sont déclenchés manuellement par l'utilisateur.
- Aucun compte ni serveur Vocalis n'est nécessaire. Les voix sont stockées sur l'ordinateur et les fichiers audio sont générés localement.
- Les moteurs audio et les modèles ONNX sont des composants tiers exécutés localement, sans sandbox fournie par Vocalis. Leur provenance, leurs mises à jour et leurs licences restent à vérifier.

Ces mesures et les tests ne constituent ni une certification de sécurité, ni une garantie contre les vulnérabilités des dépendances ou du système hôte.

## Tests et vérifications

À la racine du dossier `Vocalis/` :

```bash
python3 -m compileall -q main.py tts ui diagnostic_piper.py
python3 -m unittest discover -s tests -v
```

Les 13 tests automatisés passent avec des exécutables factices; ils couvrent notamment la validation, l'annulation, les délais, les appels des moteurs simulés, la validation WAV, le volume par blocs et l'export atomique. Ils ne remplacent pas un essai de lecture avec Piper/eSpeak NG, un test de l'interface sur une session graphique, ni l'installation du paquet Debian. Le paquet n'a pas été construit ici car `dpkg-deb` n'est pas disponible.

## Historique des versions

- **0.2.0** — Refactorisation, validation renforcée, gestion des erreurs et processus, file d'événements pour Tkinter, traitement WAV par blocs, export atomique, suppression du téléchargement de code au démarrage et ajout de tests. Voir [CHANGELOG.md](CHANGELOG.md) pour les vérifications et limites.
- **0.1.0** — Première version documentée : lecture de texte, Piper présenté comme moteur principal, eSpeak NG en solution de secours, voix française `fr_FR-siwis-medium`, utilisation hors ligne, export WAV et arrêt de la lecture.

## Organisation

```text
Vocalis/
├── main.py
├── install.sh
├── diagnostic_piper.py
├── tts/
│   ├── common.py
│   ├── espeak.py
│   ├── manager.py
│   ├── piper.py
│   └── process.py
├── ui/
│   └── app.py
├── packaging/
│   └── build-deb.sh
└── tests/
    └── test_vocalis.py
```

## Liens et crédits

- Projet Dysbuntu : [github.com/wensingmathis/Dysbuntu](https://github.com/wensingmathis/Dysbuntu)
- Sources et problèmes Vocalis : [dossier Vocalis](https://github.com/wensingmathis/Dysbuntu/tree/main/Vocalis) · [signaler un problème](https://github.com/wensingmathis/Dysbuntu/issues)
- Moteur Piper : [github.com/rhasspy/piper](https://github.com/rhasspy/piper)
- Moteur eSpeak NG : [github.com/espeak-ng/espeak-ng](https://github.com/espeak-ng/espeak-ng)
- Voix française Piper : [Piper voices sur Hugging Face](https://huggingface.co/rhasspy/piper-voices)
- Licence du dépôt : [GNU GPL-3.0](../LICENSE)

Le logo `Vocalis.jpeg` est le logo original du projet et a été conservé sans modification. Vocalis a été créé dans le cadre de Linux pour Dys. Les moteurs et modèles tiers restent soumis à leurs propres licences.
