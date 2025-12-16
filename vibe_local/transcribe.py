"""Speech-to-text transcription using faster-whisper."""
import numpy as np
from faster_whisper import WhisperModel

from .config import get_config

_model: WhisperModel | None = None


def get_model() -> WhisperModel:
    """Get or create the Whisper model instance."""
    global _model
    if _model is None:
        config = get_config().whisper
        _model = WhisperModel(
            config["model"],
            device=config["device"],
            compute_type=config["compute_type"],
        )
    return _model


def transcribe(audio: np.ndarray, sample_rate: int = 16000) -> str:
    """
    Transcribe audio data to text.

    Args:
        audio: Audio data as float32 numpy array
        sample_rate: Sample rate of the audio (default 16000)

    Returns:
        Transcribed text
    """
    if len(audio) == 0:
        return ""

    model = get_model()
    config = get_config().whisper

    # faster-whisper expects float32 audio
    if audio.dtype != np.float32:
        audio = audio.astype(np.float32)

    # Transcribe
    segments, info = model.transcribe(
        audio,
        language=config["language"] if config["language"] != "auto" else None,
        beam_size=5,
        vad_filter=True,  # Filter out non-speech
        vad_parameters=dict(
            min_silence_duration_ms=500,
        ),
    )

    # Collect all segments
    text_parts = []
    for segment in segments:
        text_parts.append(segment.text.strip())

    return " ".join(text_parts)


def transcribe_file(audio_path: str) -> str:
    """
    Transcribe an audio file to text.

    Args:
        audio_path: Path to the audio file

    Returns:
        Transcribed text
    """
    model = get_model()
    config = get_config().whisper

    segments, info = model.transcribe(
        audio_path,
        language=config["language"] if config["language"] != "auto" else None,
        beam_size=5,
        vad_filter=True,
    )

    text_parts = []
    for segment in segments:
        text_parts.append(segment.text.strip())

    return " ".join(text_parts)


def unload_model() -> None:
    """Unload the model to free GPU memory."""
    global _model
    _model = None
