# Vocalis

Vocalis est un logiciel simple pour lire du texte à voix haute sur Linux.

Il fonctionne en local, sans envoyer le texte sur Internet.

## Fonctionnalités

* Lecture de texte à voix haute
* Piper comme moteur principal
* eSpeak NG comme moteur de secours
* Voix française fr_FR-siwis-medium
* Fonctionnement hors ligne
* Aucun texte envoyé sur Internet
* Enregistrement de la voix en WAV
* Possibilité d'arrêter la lecture

## Installation

### 1. Installer les dépendances

Ouvre un terminal et fais :

```bash
sudo apt update
sudo apt install -y python3 python3-tk espeak-ng pipx
```

Puis :

```bash
pipx ensurepath
```

Ferme et rouvre le terminal.

### 2. Installer Piper

```bash
pipx install piper-tts
```

### 3. Installer la voix française

Créer le dossier :

```bash
mkdir -p ~/piper-voices
cd ~/piper-voices
```

Télécharger la voix :

```bash
wget -O fr_FR-siwis-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx?download=true"
```

Puis son fichier de configuration :

```bash
wget -O fr_FR-siwis-medium.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx.json?download=true"
```

Vérifier :

```bash
ls -lh ~/piper-voices/
```

Tu dois avoir :

```text
fr_FR-siwis-medium.onnx
fr_FR-siwis-medium.onnx.json
```

## Lancer Vocalis

Dans le dossier du logiciel :

```bash
cd ~/Téléchargements/Vocalis
python3 main.py
```

Tu peux également utiliser le raccourci Vocalis sur le bureau.

## Vérifier Piper

Pour vérifier que Piper fonctionne :

```bash
cd ~/Téléchargements/Vocalis
python3 diagnostic_piper.py
```

Le diagnostic doit trouver :

```text
/home/mathis/piper-voices/fr_FR-siwis-medium.onnx
```

## Utilisation

1. Ouvrir Vocalis
2. Choisir la voix
3. Écrire ou coller le texte
4. Cliquer sur Générer
5. Écouter la voix

Le texte reste sur l'ordinateur.

## Moteurs

### Piper

Piper est le moteur principal de Vocalis.

Voix utilisée :

fr_FR-siwis-medium

### eSpeak NG

eSpeak NG est utilisé comme moteur de secours si Piper n'est pas disponible.

## Vie privée

Vocalis fonctionne localement.

* Aucun compte nécessaire
* Aucun serveur Vocalis
* Aucun texte envoyé sur Internet
* Les voix sont stockées sur l'ordinateur
* Les fichiers audio sont générés localement

## Linux pour Dys

Vocalis fait partie du projet Linux pour Dys.

Le projet a pour objectif de créer un environnement Linux simple et accessible pour faciliter l'utilisation de l'ordinateur, notamment pour les personnes ayant des difficultés avec la lecture et l'écriture.

Le projet utilise des logiciels libres et cherche à favoriser la souveraineté numérique, la confidentialité et l'utilisation de logiciels locaux.

## Organisation

```text
Vocalis/
├── main.py
├── install.sh
├── diagnostic_piper.py
├── tts/
│   ├── espeak.py
│   ├── piper.py
│   └── manager.py
└── ui/
    └── app.py
```

## Licence

Projet libre et open source.

Créé dans le cadre du projet Linux pour Dys.
