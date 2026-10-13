"""Sound-wave transport for Acoustic Messenger.

Uses the open-source GGWave library (https://github.com/ggerganov/ggwave) to turn
text into audio and back. Works on Android (via pyjnius AudioRecord/AudioTrack)
and on desktop (via the optional `sounddevice` package) for testing.
"""
import threading
import time

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

try:
    import ggwave
except Exception:  # pragma: no cover
    ggwave = None

try:
    from kivy.utils import platform
except Exception:  # pragma: no cover
    platform = "unknown"

SAMPLE_RATE = 48000
CHUNK = 1024  # samples per read
MAX_PAYLOAD_BYTES = 140  # GGWave variable-length payload limit

# Speed names shown in the UI -> GGWave audible protocol ids
PROTOCOLS = {"Normal": 0, "Fast": 1, "Fastest": 2}


class AcousticLink:
    def __init__(self, on_payload, on_state):
        """on_payload(str) is called for every decoded message,
        on_state(str) for status changes ('listening', 'sending', 'error:...')."""
        self.on_payload = on_payload
        self.on_state = on_state
        self._running = False
        self._thread = None
        self._sending = threading.Event()
        self._instance = None
        self._stream = None  # desktop input stream

    # ------------------------------------------------------------------ utils
    @property
    def available(self):
        return ggwave is not None and np is not None

    def _feed(self, float32_bytes):
        res = ggwave.decode(self._instance, float32_bytes)
        if res is not None:
            try:
                text = res.decode("utf-8", "replace")
            except Exception:
                return
            self.on_payload(text)

    # -------------------------------------------------------------- listening
    def start_listening(self):
        if self._running:
            return
        if not self.available:
            self.on_state("error:GGWave library not available in this build")
            return
        self._running = True
        self._instance = ggwave.init()
        if platform == "android":
            self._thread = threading.Thread(target=self._android_record_loop, daemon=True)
            self._thread.start()
        else:
            self._start_desktop_input()
        self.on_state("listening")

    def stop_listening(self):
        self._running = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._thread is not None:
            self._thread.join(timeout=1.5)
            self._thread = None
        if self._instance is not None and ggwave is not None:
            try:
                ggwave.free(self._instance)
            except Exception:
                pass
            self._instance = None

    def _android_record_loop(self):
        try:
            from jnius import autoclass

            AudioRecord = autoclass("android.media.AudioRecord")
            AudioFormat = autoclass("android.media.AudioFormat")
            Source = autoclass("android.media.MediaRecorder$AudioSource")

            min_buf = AudioRecord.getMinBufferSize(
                SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT
            )
            rec = AudioRecord(
                Source.MIC,
                SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                max(min_buf, CHUNK * 2 * 8),
            )
            rec.startRecording()
            buf = bytearray(CHUNK * 2)
            while self._running:
                n = rec.read(buf, 0, len(buf))
                if n <= 0 or self._sending.is_set():
                    continue
                pcm = np.frombuffer(bytes(buf[:n]), dtype="<i2").astype(np.float32) / 32768.0
                self._feed(pcm.tobytes())
            rec.stop()
            rec.release()
        except Exception as exc:  # pragma: no cover
            self.on_state("error:microphone failed (%s)" % exc)

    def _start_desktop_input(self):
        try:
            import sounddevice as sd

            def callback(indata, frames, t, status):
                if self._sending.is_set() or not self._running:
                    return
                self._feed(indata[:, 0].astype(np.float32).tobytes())

            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                blocksize=CHUNK, callback=callback,
            )
            self._stream.start()
        except Exception as exc:
            self.on_state("error:no microphone backend (%s)" % exc)

    # ---------------------------------------------------------------- sending
    def send(self, payload, protocol=0):
        """Play `payload` as sound. Runs in a background thread."""
        threading.Thread(target=self._send_blocking, args=(payload, protocol), daemon=True).start()

    def _send_blocking(self, payload, protocol):
        if not self.available:
            self.on_state("error:GGWave library not available in this build")
            return
        self._sending.set()
        self.on_state("sending")
        try:
            wave = ggwave.encode(payload, protocolId=protocol, volume=50)
            f32 = np.frombuffer(wave, dtype=np.float32)
            seconds = len(f32) / float(SAMPLE_RATE)
            if platform == "android":
                self._android_play(f32)
            else:
                import sounddevice as sd

                sd.play(f32, SAMPLE_RATE)
                sd.wait()
            time.sleep(0.25)
        except Exception as exc:
            self.on_state("error:could not play sound (%s)" % exc)
        finally:
            self._sending.clear()
            self.on_state("listening" if self._running else "idle")

    def _android_play(self, f32):
        from jnius import autoclass

        AudioTrack = autoclass("android.media.AudioTrack")
        AudioFormat = autoclass("android.media.AudioFormat")
        AudioManager = autoclass("android.media.AudioManager")

        pcm = (np.clip(f32, -1.0, 1.0) * 32767).astype("<i2").tobytes()
        track = AudioTrack(
            AudioManager.STREAM_MUSIC,
            SAMPLE_RATE,
            AudioFormat.CHANNEL_OUT_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            len(pcm),
            AudioTrack.MODE_STATIC,
        )
        track.write(bytearray(pcm), 0, len(pcm))
        track.play()
        time.sleep(len(f32) / float(SAMPLE_RATE) + 0.3)
        track.stop()
        track.release()


def pack(username, text):
    """Build the on-air payload: 'username|text'."""
    return "%s|%s" % (username.replace("|", "").strip(), text)


def unpack(payload):
    """Split an on-air payload back into (username, text)."""
    if "|" in payload:
        name, text = payload.split("|", 1)
        return name or "Unknown", text
    return "Unknown", payload


def payload_size(username, text):
    return len(pack(username, text).encode("utf-8"))
