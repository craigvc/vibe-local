"""Cross-platform hotkey detection using pynput."""
import threading
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable

from pynput import keyboard

from .config import get_config


class HotkeyAction(Enum):
    """Available hotkey actions."""
    TRANSCRIBE = auto()
    REWRITE = auto()
    CONTEXT_REPLY = auto()


@dataclass
class HotkeyEvent:
    """Event emitted when a hotkey is triggered."""
    action: HotkeyAction
    pressed: bool  # True = pressed, False = released


# Map config key names to pynput keys
KEY_MAP = {
    "KEY_LEFTCTRL": keyboard.Key.ctrl_l,
    "KEY_RIGHTCTRL": keyboard.Key.ctrl_r,
    "KEY_LEFTSHIFT": keyboard.Key.shift_l,
    "KEY_RIGHTSHIFT": keyboard.Key.shift_r,
    "KEY_LEFTALT": keyboard.Key.alt_l,
    "KEY_RIGHTALT": keyboard.Key.alt_r,
    "KEY_LEFTMETA": keyboard.Key.cmd,  # Super/Windows/Command key
    "KEY_RIGHTMETA": keyboard.Key.cmd_r,
}


class HotkeyListener:
    """
    Cross-platform hotkey listener using pynput.

    Works on Windows, macOS, and Linux (X11 and Wayland with some limitations).
    """

    def __init__(self):
        self._config = get_config().hotkeys
        self._pressed_keys: set = set()
        self._callbacks: list[Callable[[HotkeyEvent], None]] = []
        self._listener: keyboard.Listener | None = None
        self._active_hotkey: HotkeyAction | None = None

        # Parse hotkey configs
        self._hotkeys = self._parse_hotkeys()

    def _parse_hotkeys(self) -> dict[HotkeyAction, set]:
        """Convert config key names to pynput keys."""
        result = {}

        action_map = {
            "transcribe": HotkeyAction.TRANSCRIBE,
            "rewrite": HotkeyAction.REWRITE,
            "context_reply": HotkeyAction.CONTEXT_REPLY,
        }

        for name, action in action_map.items():
            if name in self._config:
                keys = set()
                for key_name in self._config[name]:
                    if key_name in KEY_MAP:
                        keys.add(KEY_MAP[key_name])
                    elif key_name.startswith("KEY_"):
                        # Try to map single character keys like KEY_V
                        char = key_name[4:].lower()
                        if len(char) == 1:
                            keys.add(keyboard.KeyCode.from_char(char))
                        else:
                            print(f"Warning: Unknown key {key_name}")
                    else:
                        print(f"Warning: Unknown key {key_name}")
                if keys:
                    result[action] = keys

        return result

    def _normalize_key(self, key) -> keyboard.Key | keyboard.KeyCode | None:
        """Normalize a key to a consistent format."""
        # Handle special keys
        if isinstance(key, keyboard.Key):
            # Normalize left/right variants for modifiers
            if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                return keyboard.Key.ctrl_l
            elif key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
                return keyboard.Key.shift_l
            elif key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
                return keyboard.Key.alt_l
            elif key in (keyboard.Key.cmd, keyboard.Key.cmd_r):
                return keyboard.Key.cmd
            return key
        elif isinstance(key, keyboard.KeyCode):
            return key
        return None

    def add_callback(self, callback: Callable[[HotkeyEvent], None]) -> None:
        """Add a callback to be called when a hotkey is triggered."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[HotkeyEvent], None]) -> None:
        """Remove a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _emit(self, event: HotkeyEvent) -> None:
        """Emit an event to all callbacks."""
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in hotkey callback: {e}")

    def _check_hotkeys(self, is_press: bool) -> None:
        """Check if any hotkey combination is active."""
        for action, keys in self._hotkeys.items():
            if keys.issubset(self._pressed_keys):
                if is_press and self._active_hotkey is None:
                    # Hotkey pressed
                    self._active_hotkey = action
                    self._emit(HotkeyEvent(action=action, pressed=True))
            elif action == self._active_hotkey and not is_press:
                # Hotkey released
                self._active_hotkey = None
                self._emit(HotkeyEvent(action=action, pressed=False))

    def _on_press(self, key) -> None:
        """Handle key press events."""
        normalized = self._normalize_key(key)
        if normalized:
            self._pressed_keys.add(normalized)
            self._check_hotkeys(is_press=True)

    def _on_release(self, key) -> None:
        """Handle key release events."""
        normalized = self._normalize_key(key)
        if normalized:
            self._pressed_keys.discard(normalized)
            self._check_hotkeys(is_press=False)

    async def start(self) -> None:
        """Start listening for hotkeys."""
        print("Starting hotkey listener...")

        # Start the listener in a separate thread
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self._listener.start()

        print("Hotkey listener started")

        # Keep running until stopped
        while self._listener and self._listener.is_alive():
            await asyncio.sleep(0.1)

    def stop(self) -> None:
        """Stop listening for hotkeys."""
        if self._listener:
            self._listener.stop()
            self._listener = None


def check_input_permissions() -> bool:
    """Check if we have permission to listen for input events."""
    # pynput handles permissions internally
    # On Linux, may need to be run as root or with input group for some backends
    # On macOS, needs accessibility permissions
    # On Windows, generally works without special permissions
    try:
        # Try to create a listener briefly
        test_listener = keyboard.Listener(on_press=lambda k: None)
        test_listener.start()
        test_listener.stop()
        return True
    except Exception as e:
        print(f"Permission check failed: {e}")
        return False


def get_hotkey_help() -> str:
    """Get help text for configured hotkeys."""
    config = get_config().hotkeys

    def format_keys(keys: list[str]) -> str:
        # Convert evdev names to readable names
        name_map = {
            "KEY_LEFTMETA": "Super",
            "KEY_RIGHTMETA": "Super",
            "KEY_LEFTSHIFT": "Shift",
            "KEY_RIGHTSHIFT": "Shift",
            "KEY_LEFTCTRL": "Ctrl",
            "KEY_RIGHTCTRL": "Ctrl",
            "KEY_LEFTALT": "Alt",
            "KEY_RIGHTALT": "Alt",
        }
        readable = []
        for key in keys:
            if key in name_map:
                readable.append(name_map[key])
            elif key.startswith("KEY_"):
                readable.append(key[4:])
            else:
                readable.append(key)
        return "+".join(readable)

    lines = [
        "Hotkeys:",
        f"  Voice-to-text: {format_keys(config['transcribe'])}",
        f"  Rewrite selection: {format_keys(config['rewrite'])}",
        f"  Context reply: {format_keys(config['context_reply'])}",
    ]
    return "\n".join(lines)


# Need asyncio for the async start method
import asyncio
