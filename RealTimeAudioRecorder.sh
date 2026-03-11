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
    echo "Vous utilisez Windows, vérification des dépendances..."
    ;;
  *)
    echo "OS non reconnu : $OS. Cet outil utilise la librairie PyAudioWPatch qui ne fonctionne que sur Windows."
    exit 1
    ;;
esac

VENV_DIR=".venv"

# ── 1. Trouver Python 3.11 ──────────────────────────────────────────────────
PYTHON311=""
for cmd in python3.11 py python3 python; do
    if command -v "$cmd" &> /dev/null; then
        VERSION=$("$cmd" --version 2>&1 | grep -oP '3\.\d+')
        if [ "$VERSION" = "3.11" ]; then
            PYTHON311="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON311" ] && command -v py &> /dev/null; then
    py -3.11 --version &> /dev/null && PYTHON311="py -3.11"
fi

if [ -z "$PYTHON311" ]; then
    echo ""
    echo "ERREUR : Python 3.11 est requis mais introuvable."
    echo "PyAudioWPatch n'est pas compatible avec Python 3.12+."
    echo "Télécharge Python 3.11 ici : https://www.python.org/downloads/release/python-3119/"
    echo "(Coche 'Add Python to PATH' lors de l'installation)"
    exit 1
fi

echo "Python 3.11 trouvé."

# ── 2. Recréer le venv si --reset demandé ──────────────────────────────────
if [ "$1" = "--reset" ] && [ -d "$VENV_DIR" ]; then
    echo "Suppression de l'ancien environnement virtuel..."
    rm -rf "$VENV_DIR"
fi

# ── 3. Créer le venv si inexistant ─────────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "Création de l'environnement virtuel Python 3.11 dans '$VENV_DIR'..."
    $PYTHON311 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "ERREUR : Impossible de créer le venv."
        exit 1
    fi
    echo "Environnement virtuel créé."
fi

# ── 4. Chemins du venv ─────────────────────────────────────────────────────
VENV_PYTHON="$VENV_DIR/Scripts/python"
VENV_PIP="$VENV_DIR/Scripts/pip"

# ── 5. Installer / vérifier les dépendances ────────────────────────────────
$VENV_PYTHON -c "import pyaudiowpatch" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installation de PyAudioWPatch==0.2.12.6 dans le venv..."
    $VENV_PIP install --no-cache-dir "PyAudioWPatch==0.2.12.6"
    if [ $? -ne 0 ]; then
        echo "ERREUR : Echec de l'installation de PyAudioWPatch."
        exit 1
    fi
fi

$VENV_PYTHON -c "import numpy" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installation de numpy dans le venv..."
    $VENV_PIP install --no-cache-dir numpy
fi

# ── 6. Diagnostic : afficher les versions installées ──────────────────────
echo ""
echo "Versions installées :"
$VENV_PYTHON --version
$VENV_PIP show PyAudioWPatch | grep -E "^(Name|Version)"
$VENV_PIP show numpy        | grep -E "^(Name|Version)"
echo ""

# ── 7. Lancer le programme ─────────────────────────────────────────────────
echo "Lancement de RealTimeAudioRecorder.py (Python 3.11 isolé)..."
"$VENV_PYTHON" RealTimeAudioRecorder.py
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "Le programme s'est terminé avec une erreur (code $EXIT_CODE)."
    echo "Si le problème persiste, relance avec : ./RealTimeAudioRecorder.sh --reset"
    echo "Cela recréera l'environnement virtuel from scratch."
fi
