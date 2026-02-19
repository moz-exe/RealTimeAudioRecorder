import pyaudio
import wave
import threading
import sys
import os.path

# Problème d'installation de différentes lib
# pb d'utilisation de pulsaudio
# tester lib soundcard, picovoice, sounddevice & soundfile

# Audio recording parameters
FORMAT = pyaudio.paInt16 # 16-bit resolution
CHANNELS = 2             # 2: Stereo, 1: Mono
RATE = 44100             # 44.1kHz sampling rate
CHUNK = 1024             # Record in chunks of 1024 samples
BUFFER = 5               # Duration of buffer in seconds
bufferId = 0             # To name and order every buffer

path = "recordings/callRecord_"
i = 0
while (os.path.isfile(path + str(i) + "_0.wav")) :
    i += 1

outputFilePath = path + str(i) + "_"

recording = True

def record_audio():
    global recording, bufferId

    # Initialize PyAudio
    audio = pyaudio.PyAudio()

    # Open stream
    stream = audio.open(format=FORMAT,
                        input_device_index=11, # device ID or None for default
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)

    print("Recording buffer by buffer... Press Enter to stop.")

    # Record loop
    while recording:
        # Record data in buffers
        buffer_frames = []
        for _ in range(0, int(RATE / CHUNK * BUFFER)):
            data = stream.read(CHUNK)
            buffer_frames.append(data)

        # Save buffer to file
        outputFilename = outputFilePath + str(bufferId) + ".wav"
        with wave.open(outputFilename, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(buffer_frames))

        print("Recorded and saved buffer", bufferId)
        bufferId += 1

    print("Recording stopped.")

    # Stop and close stream
    stream.stop_stream()
    stream.close()
    audio.terminate()

# Thread to handle recording
recording_thread = threading.Thread(target=record_audio)
recording_thread.start()

# Wait for Enter key
input()  # Press Enter to stop
recording = False
recording_thread.join()