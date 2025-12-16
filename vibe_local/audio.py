"""Audio recording functionality."""
import io
import threading
from typing import Callable

import numpy as np
import sounddevice as sd

from .config import get_config


class AudioRecorder:
    """Records audio from the microphone."""

    def __init__(self):
        self._config = get_config().audio
        self._sample_rate = self._config["sample_rate"]
        self._channels = self._config["channels"]
        self._recording = False
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """Callback for audio stream."""
        if status:
            print(f"Audio status: {status}")
        if self._recording:
            with self._lock:
                self._frames.append(indata.copy())

    def start(self) -> None:
        """Start recording audio."""
        with self._lock:
            self._frames = []
            self._recording = True

        self._stream = sd.InputStream(
            samplerate=self._sample_rate,
            channels=self._channels,
            dtype=np.float32,
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        """Stop recording and return the audio data."""
        self._recording = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        with self._lock:
            if not self._frames:
                return np.array([], dtype=np.float32)
            audio_data = np.concatenate(self._frames, axis=0)
            self._frames = []

        # Flatten to mono if needed
        if len(audio_data.shape) > 1:
            audio_data = audio_data.mean(axis=1)

        return audio_data.astype(np.float32)

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def sample_rate(self) -> int:
        return self._sample_rate


class PushToTalkRecorder:
    """Push-to-talk style recorder that records while a condition is true."""

    def __init__(self, on_complete: Callable[[np.ndarray], None] | None = None):
        self._recorder = AudioRecorder()
        self._on_complete = on_complete
        self._is_active = False

    def press(self) -> None:
        """Called when the push-to-talk key is pressed."""
        if not self._is_active:
            self._is_active = True
            self._recorder.start()

    def release(self) -> np.ndarray | None:
        """Called when the push-to-talk key is released. Returns audio data."""
        if self._is_active:
            self._is_active = False
            audio_data = self._recorder.stop()

            if self._on_complete and len(audio_data) > 0:
                self._on_complete(audio_data)

            return audio_data
        return None

    @property
    def sample_rate(self) -> int:
        return self._recorder.sample_rate

    @property
    def is_recording(self) -> bool:
        return self._is_active


# Convenience functions
_recorder: AudioRecorder | None = None


def get_recorder() -> AudioRecorder:
    """Get the global audio recorder instance."""
    global _recorder
    if _recorder is None:
        _recorder = AudioRecorder()
    return _recorder


def record_audio_blocking(duration: float) -> np.ndarray:
    """Record audio for a fixed duration (blocking)."""
    config = get_config().audio
    sample_rate = config["sample_rate"]
    channels = config["channels"]

    audio_data = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=channels,
        dtype=np.float32,
    )
    sd.wait()

    # Flatten to mono
    if len(audio_data.shape) > 1:
        audio_data = audio_data.mean(axis=1)

    return audio_data.astype(np.float32)
