"""Transcription history manager."""
from dataclasses import dataclass
from datetime import datetime
from typing import Callable


@dataclass
class HistoryEntry:
    """A single history entry."""
    timestamp: datetime
    raw_text: str
    final_text: str
    action: str  # transcribe, rewrite, context_reply


class TranscriptionHistory:
    """Manages transcription history in memory."""

    _instance: "TranscriptionHistory | None" = None

    def __init__(self, max_entries: int = 50):
        self._entries: list[HistoryEntry] = []
        self._max_entries = max_entries
        self._callbacks: list[Callable[[], None]] = []

    @classmethod
    def get_instance(cls) -> "TranscriptionHistory":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def add(self, raw_text: str, final_text: str, action: str = "transcribe") -> None:
        """Add a new entry to history."""
        entry = HistoryEntry(
            timestamp=datetime.now(),
            raw_text=raw_text,
            final_text=final_text,
            action=action,
        )
        self._entries.insert(0, entry)

        # Trim to max entries
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[:self._max_entries]

        # Notify listeners
        for callback in self._callbacks:
            try:
                callback()
            except Exception:
                pass

    def get_entries(self) -> list[HistoryEntry]:
        """Get all history entries (newest first)."""
        return self._entries.copy()

    def clear(self) -> None:
        """Clear all history."""
        self._entries.clear()
        for callback in self._callbacks:
            try:
                callback()
            except Exception:
                pass

    def add_change_callback(self, callback: Callable[[], None]) -> None:
        """Add a callback to be notified when history changes."""
        self._callbacks.append(callback)

    def remove_change_callback(self, callback: Callable[[], None]) -> None:
        """Remove a change callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)


def get_history() -> TranscriptionHistory:
    """Get the global history instance."""
    return TranscriptionHistory.get_instance()
