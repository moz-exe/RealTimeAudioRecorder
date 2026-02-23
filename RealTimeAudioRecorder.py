import pyaudiowpatch as pyaudio
import wave
import threading
import sys
import os.path

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

    try:
        # Get default WASAPI info
        wasapi_info = audio.get_host_api_info_by_type(pyaudio.paWASAPI)
    except OSError:
        exit()

    # Get default WASAPI speakers
    default_speakers = audio.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
    
    if not default_speakers["isLoopbackDevice"]:
        for loopback in audio.get_loopback_device_info_generator():
            """
            Try to find loopback device with same name(and [Loopback suffix]).
            Unfortunately, this is the most adequate way at the moment.
            """
            if default_speakers["name"] in loopback["name"]:
                default_speakers = loopback
                break
        else:
            print("No compatible speaker found")
            exit()

    # Open stream
    stream = audio.open(format=FORMAT,
                        input_device_index=default_speakers["index"], # device ID or None for default
                        channels=default_speakers["maxInputChannels"],
                        rate=int(default_speakers["defaultSampleRate"]),
                        input=True,
                        frames_per_buffer=CHUNK
                        )

    print(f"Recording audio output from speaker : {default_speakers["name"]}")
    print(f"Sample rate : {default_speakers["defaultSampleRate"]}")
    print(f"Buffer duration : {BUFFER} seconds \n")
    print("Recording buffer by buffer... Press Enter to stop.")

    # Record loop
    while recording:
        # !!!
        # This method records data from an audio output to buffers of a specified length (duration * samplerate)
        # The buffer's timer counts only the time when audio is played
        # !!!
         
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

print("\n----------RealTimeAudioRecorder---------\n")

# Thread to handle recording
recording_thread = threading.Thread(target=record_audio)
recording_thread.start()

# Wait for Enter key
input()  # Press Enter to stop
recording = False
recording_thread.join()