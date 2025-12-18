"""Configuration management for Vibe Local."""
import os
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG = {
    "hotkeys": {
        "transcribe": ["KEY_LEFTMETA", "KEY_LEFTSHIFT", "KEY_V"],
        "rewrite": ["KEY_LEFTMETA", "KEY_LEFTSHIFT", "KEY_R"],
        "context_reply": ["KEY_LEFTMETA", "KEY_LEFTSHIFT", "KEY_C"],
    },
    "whisper": {
        "model": "medium",
        "language": "en",
        "device": "cuda",
        "compute_type": "float16",
    },
    "ollama": {
        "model": "llama3.2",
        "base_url": "http://localhost:11434",
    },
    "style": "casual",
    "vocabulary": [],
    "programming_context": "",
    "audio": {
        "sample_rate": 16000,
        "channels": 1,
    },
}


class Config:
    """Configuration container."""

    def __init__(self, config_path: str | Path | None = None):
        self._config = DEFAULT_CONFIG.copy()
        self._config_path = config_path

        if config_path:
            self.load(config_path)
        else:
            # Try to find config in standard locations
            self._try_load_default()

    def _try_load_default(self) -> None:
        """Try to load config from default locations."""
        locations = [
            Path.cwd() / "config.yaml",
            Path.home() / ".config" / "vibe-local" / "config.yaml",
            Path(__file__).parent.parent / "config.yaml",
        ]

        for path in locations:
            if path.exists():
                self.load(path)
                return

    def load(self, path: str | Path) -> None:
        """Load configuration from a YAML file."""
        path = Path(path)
        if path.exists():
            with open(path) as f:
                user_config = yaml.safe_load(f) or {}
            self._merge_config(user_config)
            self._config_path = path

    def _merge_config(self, user_config: dict[str, Any]) -> None:
        """Deep merge user config into default config."""
        for key, value in user_config.items():
            if key in self._config and isinstance(self._config[key], dict) and isinstance(value, dict):
                self._config[key].update(value)
            else:
                self._config[key] = value

    def save(self, path: str | Path | None = None) -> None:
        """Save configuration to a YAML file."""
        path = Path(path) if path else self._config_path
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                yaml.dump(self._config, f, default_flow_style=False)

    @property
    def hotkeys(self) -> dict[str, list[str]]:
        return self._config["hotkeys"]

    @property
    def whisper(self) -> dict[str, Any]:
        return self._config["whisper"]

    @property
    def ollama(self) -> dict[str, Any]:
        return self._config["ollama"]

    @property
    def style(self) -> str:
        return self._config["style"]

    @property
    def audio(self) -> dict[str, Any]:
        return self._config["audio"]

    @property
    def vocabulary(self) -> list[str]:
        return self._config.get("vocabulary", [])

    @property
    def programming_context(self) -> str:
        return self._config.get("programming_context", "")

    def __getitem__(self, key: str) -> Any:
        return self._config[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def init_config(config_path: str | Path | None = None) -> Config:
    """Initialize the global config with a specific path."""
    global _config
    _config = Config(config_path)
    return _config
