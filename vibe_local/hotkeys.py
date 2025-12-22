"""Cross-platform hotkey detection - evdev on Linux, pynput on Windows/macOS."""
import asyncio
import platform
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable

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


# Detect platform
_SYSTEM = platform.system()


if _SYSTEM == "Linux":
    # Use evdev on Linux - stable on Wayland/KDE
    import evdev
    from evdev import ecodes

    class HotkeyListener:
        """
        Linux hotkey listener using evdev.

        Directly reads from input devices - works reliably on Wayland.
        """

        def __init__(self):
            self._config = get_config().hotkeys
            self._pressed_keys: set[int] = set()
            self._callbacks: list[Callable[[HotkeyEvent], None]] = []
            self._running = False
            self._active_hotkey: HotkeyAction | None = None
            self._devices: list[evdev.InputDevice] = []

            # Parse hotkey configs (keep as evdev key names)
            self._hotkeys = self._parse_hotkeys()

        def _parse_hotkeys(self) -> dict[HotkeyAction, set[int]]:
            """Convert config key names to evdev key codes."""
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
                        if hasattr(ecodes, key_name):
                            keys.add(getattr(ecodes, key_name))
                        else:
                            print(f"Warning: Unknown key {key_name}")
                    if keys:
                        result[action] = keys

            return result

        def _find_keyboard_devices(self) -> list[evdev.InputDevice]:
            """Find all keyboard input devices."""
            devices = []
            for path in evdev.list_devices():
                try:
                    device = evdev.InputDevice(path)
                    caps = device.capabilities()
                    # Check if device has key events and looks like a keyboard
                    if ecodes.EV_KEY in caps:
                        key_caps = caps[ecodes.EV_KEY]
                        # Has letter keys = keyboard
                        if ecodes.KEY_A in key_caps and ecodes.KEY_Z in key_caps:
                            devices.append(device)
                except (PermissionError, OSError):
                    continue
            return devices

        def add_callback(self, callback: Callable[[HotkeyEvent], None]) -> None:
            self._callbacks.append(callback)

        def remove_callback(self, callback: Callable[[HotkeyEvent], None]) -> None:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

        def _emit(self, event: HotkeyEvent) -> None:
            for callback in self._callbacks:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error in hotkey callback: {e}")

        def _check_hotkeys(self, is_press: bool) -> None:
            for action, keys in self._hotkeys.items():
                if keys.issubset(self._pressed_keys):
                    if is_press and self._active_hotkey is None:
                        self._active_hotkey = action
                        self._emit(HotkeyEvent(action=action, pressed=True))
                elif action == self._active_hotkey and not is_press:
                    self._active_hotkey = None
                    self._emit(HotkeyEvent(action=action, pressed=False))

        async def _read_device(self, device: evdev.InputDevice) -> None:
            """Read events from a single device."""
            try:
                async for event in device.async_read_loop():
                    if not self._running:
                        break
                    if event.type == ecodes.EV_KEY:
                        if event.value == 1:  # Key press
                            self._pressed_keys.add(event.code)
                            self._check_hotkeys(is_press=True)
                        elif event.value == 0:  # Key release
                            self._pressed_keys.discard(event.code)
                            self._check_hotkeys(is_press=False)
            except (OSError, IOError):
                pass  # Device disconnected

        async def start(self) -> None:
            """Start listening for hotkeys."""
            print("Starting hotkey listener (evdev)...")

            self._devices = self._find_keyboard_devices()
            if not self._devices:
                print("Warning: No keyboard devices found!")
                return

            print(f"Found {len(self._devices)} keyboard device(s)")
            self._running = True

            # Read from all devices concurrently
            tasks = [self._read_device(dev) for dev in self._devices]
            await asyncio.gather(*tasks)

        def stop(self) -> None:
            self._running = False
            for device in self._devices:
                try:
                    device.close()
                except:
                    pass
            self._devices = []


    def check_input_permissions() -> bool:
        """Check if we have permission to read input devices."""
        try:
            devices = evdev.list_devices()
            if not devices:
                return False
            # Try to open at least one device
            for path in devices:
                try:
                    dev = evdev.InputDevice(path)
                    dev.close()
                    return True
                except PermissionError:
                    continue
            return False
        except Exception as e:
            print(f"Permission check failed: {e}")
            return False

else:
    # Use pynput on Windows/macOS
    from pynput import keyboard

    # Map config key names to pynput keys
    KEY_MAP = {
        "KEY_LEFTCTRL": keyboard.Key.ctrl_l,
        "KEY_RIGHTCTRL": keyboard.Key.ctrl_r,
        "KEY_LEFTSHIFT": keyboard.Key.shift_l,
        "KEY_RIGHTSHIFT": keyboard.Key.shift_r,
        "KEY_LEFTALT": keyboard.Key.alt_l,
        "KEY_RIGHTALT": keyboard.Key.alt_r,
        "KEY_LEFTMETA": keyboard.Key.cmd,
        "KEY_RIGHTMETA": keyboard.Key.cmd_r,
    }

    class HotkeyListener:
        """
        Windows/macOS hotkey listener using pynput.
        """

        def __init__(self):
            self._config = get_config().hotkeys
            self._pressed_keys: set = set()
            self._callbacks: list[Callable[[HotkeyEvent], None]] = []
            self._listener: keyboard.Listener | None = None
            self._active_hotkey: HotkeyAction | None = None
            self._hotkeys = self._parse_hotkeys()

        def _parse_hotkeys(self) -> dict[HotkeyAction, set]:
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
                            char = key_name[4:].lower()
                            if len(char) == 1:
                                keys.add(keyboard.KeyCode.from_char(char))
                    if keys:
                        result[action] = keys

            return result

        def _normalize_key(self, key):
            if isinstance(key, keyboard.Key):
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
            self._callbacks.append(callback)

        def remove_callback(self, callback: Callable[[HotkeyEvent], None]) -> None:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

        def _emit(self, event: HotkeyEvent) -> None:
            for callback in self._callbacks:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error in hotkey callback: {e}")

        def _check_hotkeys(self, is_press: bool) -> None:
            for action, keys in self._hotkeys.items():
                if keys.issubset(self._pressed_keys):
                    if is_press and self._active_hotkey is None:
                        self._active_hotkey = action
                        self._emit(HotkeyEvent(action=action, pressed=True))
                elif action == self._active_hotkey and not is_press:
                    self._active_hotkey = None
                    self._emit(HotkeyEvent(action=action, pressed=False))

        def _on_press(self, key) -> None:
            normalized = self._normalize_key(key)
            if normalized:
                self._pressed_keys.add(normalized)
                self._check_hotkeys(is_press=True)

        def _on_release(self, key) -> None:
            normalized = self._normalize_key(key)
            if normalized:
                self._pressed_keys.discard(normalized)
                self._check_hotkeys(is_press=False)

        async def start(self) -> None:
            print("Starting hotkey listener (pynput)...")
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release
            )
            self._listener.start()
            print("Hotkey listener started")

            while self._listener and self._listener.is_alive():
                await asyncio.sleep(0.1)

        def stop(self) -> None:
            if self._listener:
                self._listener.stop()
                self._listener = None


    def check_input_permissions() -> bool:
        try:
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
