import pyaudiowpatch as pyaudio
import wave
import threading
import numpy as np
import os.path
import time
import ctypes

# Audio recording parameters
FORMAT = pyaudio.paInt16  # 16-bit resolution
CHANNELS = 2              # Stereo
RATE = 44100              # 44.1kHz sampling rate
CHUNK = 1024              # Record in chunks of 1024 samples
BUFFER = 5                # Duration of buffer in seconds

path = "recordings/callRecord_"
i = 0
while os.path.isfile(path + str(i) + "_0_mixed.wav"):
    i += 1

outputFilePath = path + str(i) + "_"

recording = True

# Shared buffer storage { bufferId -> (raw_bytes, sample_rate, channels) }
speaker_buffers = {}
mic_buffers = {}
speaker_lock = threading.Lock()
mic_lock = threading.Lock()

# Mix queue
buffers_to_mix = []
mix_lock = threading.Lock()
mix_event = threading.Event()


def _notify_mix_if_ready(buf_id):
    with speaker_lock:
        has_speaker = buf_id in speaker_buffers
    with mic_lock:
        has_mic = buf_id in mic_buffers
    if has_speaker and has_mic:
        with mix_lock:
            if buf_id not in buffers_to_mix:
                buffers_to_mix.append(buf_id)
        mix_event.set()


def _ensure_stereo(array, channels):
    if channels == 1:
        return np.repeat(array, 2)
    return array


def _read_chunk_with_timeout(stream, chunk_size, timeout_s):
    """Reads one chunk from stream in a sub-thread.
    Returns the chunk, or a silence chunk if the read exceeds timeout_s."""
    result = [None]
    def _read():
        try:
            result[0] = stream.read(chunk_size, exception_on_overflow=False)
        except Exception:
            result[0] = None

    t = threading.Thread(target=_read, daemon=True)
    t.start()
    t.join(timeout=timeout_s)
    return result[0]  # None if timed out


def record_speaker(audio):
    """Records system audio output (loopback) in real-time 5s buffers.
    Uses a per-chunk timeout to inject silence when no sound is playing,
    keeping the speaker stream wall-clock aligned with the mic stream."""
    global recording

    try:
        wasapi_info = audio.get_host_api_info_by_type(pyaudio.paWASAPI)
    except OSError:
        print("[Speaker] WASAPI not found.")
        return

    default_speakers = audio.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
    if not default_speakers["isLoopbackDevice"]:
        for loopback in audio.get_loopback_device_info_generator():
            if default_speakers["name"] in loopback["name"]:
                default_speakers = loopback
                break
        else:
            print("[Speaker] No compatible loopback device found.")
            return

    spk_rate = int(default_speakers["defaultSampleRate"])
    spk_channels = default_speakers["maxInputChannels"]
    frames_per_buffer = int(spk_rate / CHUNK * BUFFER)
    # Timeout slightly longer than one chunk duration to tolerate jitter
    chunk_duration = CHUNK / spk_rate
    read_timeout = chunk_duration * 4
    silence_chunk = b'\x00' * CHUNK * spk_channels * 2

    stream = audio.open(
        format=FORMAT,
        input_device_index=default_speakers["index"],
        channels=spk_channels,
        rate=spk_rate,
        input=True,
        frames_per_buffer=CHUNK
    )

    print(f"[Speaker] Device      : {default_speakers['name']}")
    print(f"[Speaker] Sample rate : {spk_rate} Hz | Channels : {spk_channels}")

    local_id = 0
    while recording:
        buffer_frames = []
        deadline = time.monotonic() + BUFFER

        while time.monotonic() < deadline:
            if not recording:
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            # Use min(read_timeout, remaining) so we never overshoot the deadline
            timeout = min(read_timeout, remaining)
            chunk = _read_chunk_with_timeout(stream, CHUNK, timeout)
            if chunk is None:
                # No sound playing: inject silence to keep wall-clock pace
                elapsed_in_silence = timeout
                silence_chunks_needed = max(1, int(elapsed_in_silence / chunk_duration))
                for _ in range(silence_chunks_needed):
                    buffer_frames.append(silence_chunk)
            else:
                buffer_frames.append(chunk)

        # Trim or pad to exact buffer length
        buffer_frames = buffer_frames[:frames_per_buffer]
        while len(buffer_frames) < frames_per_buffer:
            buffer_frames.append(silence_chunk)

        with speaker_lock:
            speaker_buffers[local_id] = (b''.join(buffer_frames), spk_rate, spk_channels)

        print(f"[Speaker] Buffer {local_id} captured")
        _notify_mix_if_ready(local_id)
        local_id += 1

    stream.stop_stream()
    stream.close()
    print("[Speaker] Stopped.")


def record_microphone(audio):
    """Records microphone input in real-time 5s buffers (wall-clock timed)."""
    global recording

    try:
        wasapi_info = audio.get_host_api_info_by_type(pyaudio.paWASAPI)
    except OSError:
        print("[Mic] WASAPI not found.")
        return

    default_mic_index = wasapi_info["defaultInputDevice"]
    default_mic = audio.get_device_info_by_index(default_mic_index)
    mic_rate = int(default_mic["defaultSampleRate"])
    mic_channels = min(default_mic["maxInputChannels"], CHANNELS)
    frames_per_buffer = int(mic_rate / CHUNK * BUFFER)
    silence_chunk = b'\x00' * CHUNK * mic_channels * 2

    stream = audio.open(
        format=FORMAT,
        input_device_index=default_mic_index,
        channels=mic_channels,
        rate=mic_rate,
        input=True,
        frames_per_buffer=CHUNK
    )

    print(f"[Mic]     Device      : {default_mic['name']}")
    print(f"[Mic]     Sample rate : {mic_rate} Hz | Channels : {mic_channels}\n")

    local_id = 0
    while recording:
        buffer_frames = []
        deadline = time.monotonic() + BUFFER

        while time.monotonic() < deadline:
            if not recording:
                break
            data = stream.read(CHUNK, exception_on_overflow=False)
            buffer_frames.append(data)

        while len(buffer_frames) < frames_per_buffer:
            buffer_frames.append(silence_chunk)

        with mic_lock:
            mic_buffers[local_id] = (b''.join(buffer_frames), mic_rate, mic_channels)

        print(f"[Mic]     Buffer {local_id} captured")
        _notify_mix_if_ready(local_id)
        local_id += 1

    stream.stop_stream()
    stream.close()
    print("[Mic] Stopped.")


def mix_and_save():
    """Waits for paired buffers, mixes them and saves the result as .wav."""
    os.makedirs("recordings", exist_ok=True)

    while recording or buffers_to_mix:
        mix_event.wait(timeout=1.0)
        mix_event.clear()

        while True:
            with mix_lock:
                if not buffers_to_mix:
                    break
                buf_id = buffers_to_mix.pop(0)

            with speaker_lock:
                spk_data, spk_rate, spk_ch = speaker_buffers.pop(buf_id)
            with mic_lock:
                mic_data, mic_rate, mic_ch = mic_buffers.pop(buf_id)

            spk = np.frombuffer(spk_data, dtype=np.int16).astype(np.int32)
            mic = np.frombuffer(mic_data, dtype=np.int16).astype(np.int32)

            spk = _ensure_stereo(spk, spk_ch)
            mic = _ensure_stereo(mic, mic_ch)

            length = max(len(spk), len(mic))
            if len(spk) < length:
                spk = np.pad(spk, (0, length - len(spk)))
            if len(mic) < length:
                mic = np.pad(mic, (0, length - len(mic)))

            mixed = np.clip(spk + mic, -32768, 32767).astype(np.int16)

            filename = outputFilePath + str(buf_id) + "_mixed.wav"
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(2)
                wf.setframerate(RATE)
                wf.writeframes(mixed.tobytes())

            print(f"[Mixer]   Buffer {buf_id} saved → {filename}")

    print("[Mixer] Done.")


# ─── Main ───────────────────────────────────────────────────────────────────

print("\n----------RealTimeAudioRecorder---------\n")
print("Recording buffer by buffer... Press Enter to stop.\n")

audio = pyaudio.PyAudio()

speaker_thread = threading.Thread(target=record_speaker, args=(audio,), daemon=True)
mic_thread     = threading.Thread(target=record_microphone, args=(audio,), daemon=True)
mixer_thread   = threading.Thread(target=mix_and_save, daemon=True)

speaker_thread.start()
mic_thread.start()
mixer_thread.start()

input()  # Press Enter to stop
recording = False
mix_event.set()

speaker_thread.join()
mic_thread.join()
mixer_thread.join()

audio.terminate()
print("\nAll threads finished. Goodbye.")
