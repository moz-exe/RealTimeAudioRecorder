#!/bin/bash

# Détection du système d'exploitation
OS="$(uname -s)"
case "$OS" in
  Linux*)
    echo "Vous utilisez Linux, cet outil utilise la librairie PyAudioWPatch qui ne fonctionne que sur Windows."
    exit 1
    ;;
  Darwin*)
    echo "Vous utilisez macOS, cet outil utilise la librairie PyAudioWPatch qui ne fonctionne que sur Windows."
    exit 1
    ;;
  CYGWIN*|MINGW32*|MSYS*|MINGW*)
    # Windows
    echo "Vous utilisez Windows, vérification des dépendances..."
    ;;
  *)
    echo "OS non reconnu : $OS. Cet outil utilise la librairie PyAudioWPatch qui ne fonctionne que sur Windows."
    exit 1
    ;;
esac

# Vérification de pip
if ! command -v pip &> /dev/null; then
    echo "pip n'est pas installé. Installation en cours..."
    python3 -m ensurepip --upgrade
fi

# Vérification et installation des dépendances Python
python3 -c "import pkg_resources; exit(0 if pkg_resources.get_distribution('PyAudioWPatch', None) else 1)" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installation de PyAudioWPatch..."
    pip install PyAudioWPatch
fi

# Exécution du programme
echo "Lancement de RealTimeAudioRecorder.py..."
python3 RealTimeAudioRecorder.py
