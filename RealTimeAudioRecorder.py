import pyaudiowpatch as pyaudio
import wave
import threading
import numpy as np
import os
import time


class AudioRecorder:
    """
    Enregistre simultanément le microphone et la sortie audio système (loopback WASAPI),
    mélange les deux flux et sauvegarde le résultat en fichiers .wav de 5 secondes.

    Utilisation :
        recorder = RealTimeAudioRecorder()
        recorder.record()
        ...
        recorder.stop_recording()
    """

    # Audio recording parameters
    FORMAT  = pyaudio.paInt16  # 16-bit resolution
    CHANNELS = 2               # Stereo
    RATE    = 44100            # 44.1kHz sampling rate
    CHUNK   = 1024             # Samples per chunk
    BUFFER  = 5                # Buffer duration in seconds

    def __init__(self):
        self.output_dir = "recordings"
        self.base_name  = "callRecord"

        # Chaque instance a son propre état — pas de globals
        self._audio          = None
        self._speaker_thread = None
        self._mic_thread     = None
        self._mixer_thread   = None
        self._recording      = False

        self._speaker_buffers = {}
        self._mic_buffers     = {}
        self._speaker_lock    = threading.Lock()
        self._mic_lock        = threading.Lock()

        self._buffers_to_mix  = []
        self._mix_lock        = threading.Lock()
        self._mix_event       = threading.Event()
        self._recorders_done  = threading.Event()

        self._output_file_path = self._next_output_path()

# -------------------- Public Methods --------------------
    def record(self):
        """Lance l'enregistrement en arrière-plan (non bloquant)."""
        if self._recording:
            raise RuntimeError("Un enregistrement est déjà en cours.")

        self._reset_state()
        self._output_file_path = self._next_output_path()

        print("\n----------RealTimeAudioRecorder---------\n")
        print(f"Fichiers de sortie : {self._output_file_path}*.wav")
        print("Enregistrement en cours...\n")

        self._recording = True
        self._audio = pyaudio.PyAudio()

        self._speaker_thread = threading.Thread(target=self._record_speaker, daemon=True)
        self._mic_thread = threading.Thread(target=self._record_microphone, daemon=True)
        self._mixer_thread = threading.Thread(target=self._mix_and_save, daemon=True)

        self._speaker_thread.start()
        self._mic_thread.start()
        self._mixer_thread.start()

    def stop_recording(self):
        """Arrête l'enregistrement et attend la fin propre de tous les threads."""
        if not self._recording:
            raise RuntimeError("Aucun enregistrement en cours.")

        self._recording = False

        # Attendre que les deux threads aient posté leur dernier buffer
        self._speaker_thread.join()
        self._mic_thread.join()

        # Signaler au mixer que plus aucun buffer n'arrivera
        self._recorders_done.set()
        self._mix_event.set()
        self._mixer_thread.join()

        # Ne pas appeler audio.terminate() : Pa_Terminate() crash avec un
        # segfault sur Windows quand un device loopback WASAPI a été utilisé
        # (bug connu PyAudioWPatch/PortAudio). Les ressources sont libérées
        # proprement par Windows, soit à la fin du processus, soit lors du
        # prochain PyAudio() qui appelle Pa_Initialize() et repart de zéro.
        self._audio = None

        print("\nAll threads finished. Goodbye.")

#-------------------- Private Methods --------------------
    def _reset_state(self):
        """Remet à zéro tous les buffers et événements pour une nouvelle session."""
        self._speaker_buffers.clear()
        self._mic_buffers.clear()
        self._buffers_to_mix.clear()
        self._mix_event.clear()
        self._recorders_done.clear()

    def _next_output_path(self):
        """Calcule le prochain préfixe de fichier disponible (ex: recordings/callRecord_3_)."""
        os.makedirs(self.output_dir, exist_ok=True)
        i = 0
        while os.path.isfile(
                os.path.join(self.output_dir, f"{self.base_name}_{i}_0.wav")):
            i += 1
        return os.path.join(self.output_dir, f"{self.base_name}_{i}_")

    def _notify_mix_if_ready(self, buf_id):
        with self._speaker_lock:
            has_speaker = buf_id in self._speaker_buffers
        with self._mic_lock:
            has_mic = buf_id in self._mic_buffers
        if has_speaker and has_mic:
            with self._mix_lock:
                if buf_id not in self._buffers_to_mix:
                    self._buffers_to_mix.append(buf_id)
            self._mix_event.set()

    @staticmethod
    def _ensure_stereo(array, channels):
        if channels == 1:
            return np.repeat(array, 2)
        return array

    @staticmethod
    def _read_chunk_with_timeout(stream, chunk_size, timeout_s):
        result = [None]
        def _read():
            try:
                result[0] = stream.read(chunk_size, exception_on_overflow=False)
            except Exception:
                result[0] = None
        t = threading.Thread(target=_read, daemon=True)
        t.start()
        t.join(timeout=timeout_s)
        return result[0]

    @staticmethod
    def _close_stream_safely(stream):
        try:
            stream.stop_stream()
        except Exception:
            pass
        try:
            stream.close()
        except Exception:
            pass

#-------------------- Recording Threads --------------------
    def _record_speaker(self):
        try:
            wasapi_info = self._audio.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError:
            print("[Speaker] WASAPI not found.")
            return

        default_speakers = self._audio.get_device_info_by_index(
            wasapi_info["defaultOutputDevice"])
        if not default_speakers["isLoopbackDevice"]:
            for loopback in self._audio.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    default_speakers = loopback
                    break
            else:
                print("[Speaker] No compatible loopback device found.")
                return

        spk_rate     = int(default_speakers["defaultSampleRate"])
        spk_channels = default_speakers["maxInputChannels"]
        frames_per_buffer = int(spk_rate / self.CHUNK * self.BUFFER)
        chunk_duration    = self.CHUNK / spk_rate
        read_timeout      = chunk_duration * 4
        silence_chunk     = b'\x00' * self.CHUNK * spk_channels * 2

        stream = self._audio.open(
            format=self.FORMAT,
            input_device_index=default_speakers["index"],
            channels=spk_channels,
            rate=spk_rate,
            input=True,
            frames_per_buffer=self.CHUNK
        )

        print(f"[Speaker] Device      : {default_speakers['name']}")
        print(f"[Speaker] Sample rate : {spk_rate} Hz | Channels : {spk_channels}")

        local_id = 0
        while self._recording:
            buffer_frames = []
            deadline = time.monotonic() + self.BUFFER

            while time.monotonic() < deadline:
                if not self._recording:
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                timeout = min(read_timeout, remaining)
                chunk = self._read_chunk_with_timeout(stream, self.CHUNK, timeout)
                if chunk is None:
                    silence_chunks_needed = max(1, int(timeout / chunk_duration))
                    for _ in range(silence_chunks_needed):
                        buffer_frames.append(silence_chunk)
                else:
                    buffer_frames.append(chunk)

            buffer_frames = buffer_frames[:frames_per_buffer]
            while len(buffer_frames) < frames_per_buffer:
                buffer_frames.append(silence_chunk)

            with self._speaker_lock:
                self._speaker_buffers[local_id] = (
                    b''.join(buffer_frames), spk_rate, spk_channels)

            print(f"[Speaker] Buffer {local_id} captured")
            self._notify_mix_if_ready(local_id)
            local_id += 1

        self._close_stream_safely(stream)
        print("[Speaker] Stopped.")

    def _record_microphone(self):
        try:
            wasapi_info = self._audio.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError:
            print("[Mic] WASAPI not found.")
            return

        default_mic_index = wasapi_info["defaultInputDevice"]
        default_mic  = self._audio.get_device_info_by_index(default_mic_index)
        mic_rate     = int(default_mic["defaultSampleRate"])
        mic_channels = min(default_mic["maxInputChannels"], self.CHANNELS)
        frames_per_buffer = int(mic_rate / self.CHUNK * self.BUFFER)
        silence_chunk     = b'\x00' * self.CHUNK * mic_channels * 2

        stream = self._audio.open(
            format=self.FORMAT,
            input_device_index=default_mic_index,
            channels=mic_channels,
            rate=mic_rate,
            input=True,
            frames_per_buffer=self.CHUNK
        )

        print(f"[Mic]     Device      : {default_mic['name']}")
        print(f"[Mic]     Sample rate : {mic_rate} Hz | Channels : {mic_channels}\n")

        local_id = 0
        while self._recording:
            buffer_frames = []
            deadline = time.monotonic() + self.BUFFER

            while time.monotonic() < deadline:
                if not self._recording:
                    break
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                buffer_frames.append(data)

            while len(buffer_frames) < frames_per_buffer:
                buffer_frames.append(silence_chunk)

            with self._mic_lock:
                self._mic_buffers[local_id] = (
                    b''.join(buffer_frames), mic_rate, mic_channels)

            print(f"[Mic]     Buffer {local_id} captured")
            self._notify_mix_if_ready(local_id)
            local_id += 1

        self._close_stream_safely(stream)
        print("[Mic] Stopped.")

    def _mix_and_save(self):
        os.makedirs(self.output_dir, exist_ok=True)

        while True:
            self._mix_event.wait(timeout=0.2)
            self._mix_event.clear()

            while True:
                with self._mix_lock:
                    if not self._buffers_to_mix:
                        break
                    buf_id = self._buffers_to_mix.pop(0)

                with self._speaker_lock:
                    spk_data, spk_rate, spk_ch = self._speaker_buffers.pop(buf_id)
                with self._mic_lock:
                    mic_data, mic_rate, mic_ch = self._mic_buffers.pop(buf_id)

                spk = np.frombuffer(spk_data, dtype=np.int16).astype(np.int32)
                mic = np.frombuffer(mic_data, dtype=np.int16).astype(np.int32)

                spk = self._ensure_stereo(spk, spk_ch)
                mic = self._ensure_stereo(mic, mic_ch)

                length = max(len(spk), len(mic))
                if len(spk) < length:
                    spk = np.pad(spk, (0, length - len(spk)))
                if len(mic) < length:
                    mic = np.pad(mic, (0, length - len(mic)))

                mixed = np.clip(spk + mic, -32768, 32767).astype(np.int16)

                filename = self._output_file_path + str(buf_id) + ".wav"
                with wave.open(filename, 'wb') as wf:
                    wf.setnchannels(self.CHANNELS)
                    wf.setsampwidth(2)
                    wf.setframerate(self.RATE)
                    wf.writeframes(mixed.tobytes())

                print(f"[Mixer]   Buffer {buf_id} saved → {filename}")

            if self._recorders_done.is_set():
                with self._mix_lock:
                    if not self._buffers_to_mix:
                        break

        print("[Mixer] Done.")



if __name__ == "__main__":
    recorder = AudioRecorder()
    recorder.record()
    input("Press Enter to stop...\n")
    recorder.stop_recording()
    # FIX : os._exit() contourne le cleanup Python/PortAudio qui cause le segfault.
    # Tous les fichiers .wav sont deja fermes et flushed a ce stade.
    os._exit(0)
