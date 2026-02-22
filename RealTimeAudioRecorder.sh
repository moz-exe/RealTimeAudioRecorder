#!/bin/bash

# Détection de l'OS
OS="$(uname -s 2>/dev/null || echo "Windows")"

# Fonction pour vérifier et installer Python et pip
install_python_pip() {
    if [[ "$OS" == "Windows"* ]]; then
        # Exécute les commandes PowerShell pour Windows
        powershell -Command "
            if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
                Write-Host 'Python n''est pas installé. Installation en cours...'
                winget install Python.Python.3 -h
                if (-not (\$?)) {
                    Write-Host 'Erreur : Impossible d''installer Python.'
                    exit 1
                }
            }
            if (-not (Get-Command pip -ErrorAction SilentlyContinue)) {
                Write-Host 'pip n''est pas installé. Installation en cours...'
                python -m ensurepip --upgrade
            }
        "
    else
        # Commandes pour Linux/macOS
        if ! command -v python3 &> /dev/null; then
            echo "Python 3 n'est pas installé. Installation en cours..."
            if [[ "$OS" == "Linux"* ]]; then
                sudo apt-get update && sudo apt-get install -y python3 python3-pip
            elif [[ "$OS" == "Darwin"* ]]; then
                brew install python
            fi
        fi
        if ! command -v pip3 &> /dev/null; then
            # if [[ "$OS" == "Linux"* ]]; then
                # sudo apt-get update && sudo apt-get install -y python3-pip
            if [[ "$OS" == "Darwin"* ]]; then
                echo "pip3 n'est pas installé. Installation en cours..."
                curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
                python3 get-pip.py
                rm get-pip.py
            fi
        fi
    fi
}

# Fonction pour installer pyaudio
install_pyaudiowpatch() {
    if [[ "$OS" == "Windows"* ]]; then
        powershell -Command "
            if (-not (python -c 'import PyAudioWPatch' 2>\$null)) {
                Write-Host 'Installation de PyAudioWPatch...'
                python -m pip install PyAudioWPatch
            }
        "
    # else
    #     if ! python3 -c "import pyaudio" 2>/dev/null; then
    #         echo "Installation de pyaudio..."
    #         if [[ "$OS" == "Linux"* ]]; then
    #             sudo apt-get update && sudo apt-get install -y portaudio19-dev python3-pyaudio
    #         elif [[ "$OS" == "Darwin"* ]]; then
    #             brew install portaudio
    #             pip3 install pyaudio
    #         fi
    #     fi
    fi
}

if [[ "$OS" != "Windows"* ]]; then
    echo "Vous utilisez $OS, cet outil utilise la librairie PyAudioWPatch qui ne fonctionne que sur Windows"
    exit
fi

# Vérification de Python et pip
install_python_pip

# Vérification de pyaudio
install_pyaudiowpatch

# Vérification du fichier RealTimeAudioRecorder.py
if [[ "$OS" == "Windows"* ]]; then
    powershell -Command "
        if (-not (Test-Path 'RealTimeAudioRecorder.py')) {
            Write-Host 'Erreur : Le fichier RealTimeAudioRecorder.py n''existe pas.'
            exit 1
        }
    "
else
    if [ ! -f "RealTimeAudioRecorder.py" ]; then
        echo "Erreur : Le fichier RealTimeAudioRecorder.py n'existe pas dans le répertoire courant."
        exit 1
    fi
fi

# Exécution du programme
if [[ "$OS" == "Windows"* ]]; then
    powershell -Command "python RealTimeAudioRecorder.py"
else
    python3 RealTimeAudioRecorder.py
fi
