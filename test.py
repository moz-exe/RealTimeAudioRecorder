import soundcard as sc
import soundfile as sf
import time
import numpy as np

# Paramètres audio
CHANNELS = 1  # 2: Stéréo, 1: Mono
RATE = 48000  # Fréquence d'échantillonnage (48kHz est courant pour soundcard)

# Liste des microphones disponibles
mics = sc.all_microphones(include_loopback=True)
default_mic = sc.default_microphone()

# Afficher les microphones disponibles
for i, mic in enumerate(mics):
    try:
        print(f"{i}: {mic.name}")
    except Exception as e:
        print(e)

# Enregistrement
with default_mic.recorder(samplerate=RATE) as mic:
    print("Enregistrement en cours...")
    data = mic.record(numframes=int(0.1 * RATE))  # Enregistre 0.1 secondes
    print("Enregistrement terminé.")

    # Convertir les données en int16 (PCM_16)
    data_int16 = (data.T * 32767).astype(np.int16)

    print(f"Forme des données : {data.shape}")  # Devrait être (N, CHANNELS)
    print(f"Données : {data}")


    # Sauvegarde du fichier WAV
    output_filename = "test.wav"
    sf.write(output_filename, data_int16, RATE,channels=CHANNELS)
    print(f"Fichier enregistré sous {output_filename}")
