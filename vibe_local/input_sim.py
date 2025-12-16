"""Cross-platform input simulation using pynput and pyperclip."""
import platform
import shutil
import subprocess
import time
from typing import Optional

import pyperclip
from pynput.keyboard import Controller, Key


# Keyboard controller for typing and key simulation
_keyboard = Controller()

# Cache for tool availability
_tool_cache: dict[str, bool] = {}


def _check_tool(name: str) -> bool:
    """Check if a tool is available (cached)."""
    if name not in _tool_cache:
        _tool_cache[name] = shutil.which(name) is not None
    return _tool_cache[name]


def check_dependencies() -> dict[str, bool]:
    """Check if required tools are available."""
    results = {
        "pynput": True,
        "pyperclip": True,
    }

    # Test clipboard access
    try:
        pyperclip.paste()
    except pyperclip.PyperclipException:
        results["pyperclip"] = False

    # On Linux, check for ydotool (preferred for Wayland)
    if platform.system() == "Linux":
        results["ydotool"] = _check_tool("ydotool")

    return results


def type_text(text: str, interval: float = 0.01) -> bool:
    """
    Type text at the current cursor position.

    On Linux, uses ydotool for Wayland compatibility.
    On other platforms, uses pynput.

    Args:
        text: Text to type
        interval: Delay between keystrokes (seconds)

    Returns:
        True if successful
    """
    if not text:
        return True

    system = platform.system()

    # On Linux, prefer ydotool for Wayland compatibility
    if system == "Linux" and _check_tool("ydotool"):
        try:
            # ydotool works on KDE Wayland (pynput/wtype don't)
            key_delay = int(interval * 1000)  # Convert to milliseconds
            result = subprocess.run(
                ["ydotool", "type", "--key-delay", str(key_delay), "--", text],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return True
            print(f"ydotool failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            print("ydotool timed out")
        except Exception as e:
            print(f"ydotool error: {e}")
        # Fall through to pynput fallback

    # Use pynput for Windows, macOS, or Linux fallback
    try:
        for char in text:
            _keyboard.type(char)
            if interval > 0:
                time.sleep(interval)
        return True
    except Exception as e:
        print(f"Error typing text: {e}")
        return False


def type_text_fast(text: str) -> bool:
    """
    Type text quickly using clipboard paste method.

    This is faster for long text but may not work in all applications.

    Args:
        text: Text to type

    Returns:
        True if successful
    """
    if not text:
        return True

    try:
        # Save current clipboard
        old_clipboard = get_clipboard()

        # Set text to clipboard and paste
        set_clipboard(text)
        time.sleep(0.05)  # Small delay for clipboard to update
        paste_from_clipboard()
        time.sleep(0.1)  # Wait for paste to complete

        # Restore old clipboard
        if old_clipboard:
            set_clipboard(old_clipboard)

        return True
    except Exception as e:
        print(f"Error typing text (fast): {e}")
        return False


def get_clipboard() -> str:
    """
    Get text from the clipboard.

    Returns:
        Clipboard contents or empty string
    """
    try:
        return pyperclip.paste() or ""
    except pyperclip.PyperclipException as e:
        print(f"Error getting clipboard: {e}")
        return ""
    except Exception as e:
        print(f"Error getting clipboard: {e}")
        return ""


def set_clipboard(text: str) -> bool:
    """
    Set text to the clipboard.

    Args:
        text: Text to copy to clipboard

    Returns:
        True if successful
    """
    try:
        pyperclip.copy(text)
        return True
    except pyperclip.PyperclipException as e:
        print(f"Error setting clipboard: {e}")
        return False
    except Exception as e:
        print(f"Error setting clipboard: {e}")
        return False


def get_selection() -> str:
    """
    Get the current text selection.

    On Linux, this gets the primary selection (X11/Wayland).
    On Windows/macOS, this simulates Ctrl+C/Cmd+C and gets clipboard.

    Returns:
        Selected text or empty string
    """
    system = platform.system()

    if system == "Linux":
        # Try to get primary selection on Linux
        try:
            import subprocess
            # Try wl-paste for Wayland
            result = subprocess.run(
                ["wl-paste", "--primary", "--no-newline"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                return result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        try:
            # Try xclip for X11
            import subprocess
            result = subprocess.run(
                ["xclip", "-selection", "primary", "-o"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                return result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    # Fallback: copy selection to clipboard and read it
    old_clipboard = get_clipboard()
    copy_selection()
    time.sleep(0.1)  # Wait for copy to complete
    selection = get_clipboard()

    # Restore old clipboard if we got a selection
    if selection and old_clipboard != selection:
        set_clipboard(old_clipboard)

    return selection


def set_selection(text: str) -> bool:
    """
    Set the primary selection (Linux) or clipboard (other platforms).

    Args:
        text: Text to set as selection

    Returns:
        True if successful
    """
    system = platform.system()

    if system == "Linux":
        # Try to set primary selection on Linux
        try:
            import subprocess
            result = subprocess.run(
                ["wl-copy", "--primary"],
                input=text,
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        try:
            import subprocess
            result = subprocess.run(
                ["xclip", "-selection", "primary"],
                input=text,
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    # Fallback to clipboard
    return set_clipboard(text)


def paste_from_clipboard() -> bool:
    """
    Simulate Ctrl+V (or Cmd+V on macOS) to paste from clipboard.

    Returns:
        True if successful
    """
    try:
        system = platform.system()
        if system == "Darwin":
            # macOS uses Cmd+V
            with _keyboard.pressed(Key.cmd):
                _keyboard.press('v')
                _keyboard.release('v')
        else:
            # Windows and Linux use Ctrl+V
            with _keyboard.pressed(Key.ctrl):
                _keyboard.press('v')
                _keyboard.release('v')
        return True
    except Exception as e:
        print(f"Error pasting: {e}")
        return False


def copy_selection() -> bool:
    """
    Simulate Ctrl+C (or Cmd+C on macOS) to copy selection to clipboard.

    Returns:
        True if successful
    """
    try:
        system = platform.system()
        if system == "Darwin":
            # macOS uses Cmd+C
            with _keyboard.pressed(Key.cmd):
                _keyboard.press('c')
                _keyboard.release('c')
        else:
            # Windows and Linux use Ctrl+C
            with _keyboard.pressed(Key.ctrl):
                _keyboard.press('c')
                _keyboard.release('c')
        return True
    except Exception as e:
        print(f"Error copying: {e}")
        return False


def press_key(key: str) -> bool:
    """
    Press and release a single key.

    Args:
        key: Key to press (e.g., 'a', 'enter', 'backspace')

    Returns:
        True if successful
    """
    try:
        # Map common key names to pynput Keys
        key_map = {
            'enter': Key.enter,
            'return': Key.enter,
            'tab': Key.tab,
            'space': Key.space,
            'backspace': Key.backspace,
            'delete': Key.delete,
            'escape': Key.esc,
            'esc': Key.esc,
            'up': Key.up,
            'down': Key.down,
            'left': Key.left,
            'right': Key.right,
            'home': Key.home,
            'end': Key.end,
            'pageup': Key.page_up,
            'pagedown': Key.page_down,
        }

        key_lower = key.lower()
        if key_lower in key_map:
            _keyboard.press(key_map[key_lower])
            _keyboard.release(key_map[key_lower])
        else:
            # Assume it's a character
            _keyboard.press(key)
            _keyboard.release(key)

        return True
    except Exception as e:
        print(f"Error pressing key: {e}")
        return False


def select_all() -> bool:
    """
    Simulate Ctrl+A (or Cmd+A on macOS) to select all text.

    Returns:
        True if successful
    """
    try:
        system = platform.system()
        if system == "Darwin":
            with _keyboard.pressed(Key.cmd):
                _keyboard.press('a')
                _keyboard.release('a')
        else:
            with _keyboard.pressed(Key.ctrl):
                _keyboard.press('a')
                _keyboard.release('a')
        return True
    except Exception as e:
        print(f"Error selecting all: {e}")
        return False
