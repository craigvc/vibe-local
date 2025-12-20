"""Main application - system tray and event coordination."""
import asyncio
import signal
import subprocess
import sys
import threading

from .audio import PushToTalkRecorder
from .config import get_config, init_config
from .history import get_history
from .hotkeys import HotkeyAction, HotkeyEvent, HotkeyListener, check_input_permissions, get_hotkey_help
from .input_sim import check_dependencies, get_clipboard, get_selection, type_text
from .llm import check_ollama_available, context_reply, ensure_model_available, improve_transcription, rewrite
from .transcribe import transcribe
from .tray_qt import VibeTray


class VibeLocal:
    """Main application class."""

    def __init__(self):
        self._recorder = PushToTalkRecorder()
        self._hotkey_listener = HotkeyListener()
        self._tray: VibeTray | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._current_action: HotkeyAction | None = None
        self._running = False

    def _notify(self, message: str, title: str = "Vibe Local") -> None:
        """Show a desktop notification."""
        if self._tray:
            self._tray.notify(message, title)
        else:
            try:
                subprocess.run(
                    ["notify-send", "-t", "2000", title, message],
                    capture_output=True,
                    timeout=2,
                )
            except Exception:
                pass
        print(f"[{title}] {message}")

    def _handle_hotkey(self, event: HotkeyEvent) -> None:
        """Handle hotkey events."""
        if event.pressed:
            # Start recording
            self._current_action = event.action
            self._recorder.press()

            if self._tray:
                self._tray.set_recording(True)

            action_names = {
                HotkeyAction.TRANSCRIBE: "Recording...",
                HotkeyAction.REWRITE: "Recording rewrite instruction...",
                HotkeyAction.CONTEXT_REPLY: "Recording reply intent...",
            }
            msg = action_names.get(event.action, "Recording...")
            print(f"\n>>> {msg}")
            self._notify(msg)

        else:
            # Stop recording and process
            if self._tray:
                self._tray.set_recording(False)

            audio_data = self._recorder.release()

            if audio_data is not None and len(audio_data) > 0:
                # Process in a thread to not block
                threading.Thread(
                    target=self._process_audio,
                    args=(audio_data, self._current_action),
                    daemon=True,
                ).start()

            self._current_action = None

    def _process_audio(self, audio_data, action: HotkeyAction) -> None:
        """Process recorded audio based on the action."""
        try:
            print(">>> Transcribing...")
            self._notify("Transcribing...")

            # Transcribe the audio
            text = transcribe(audio_data, self._recorder.sample_rate)
            print(f">>> Raw: {text}")

            if not text.strip():
                print(">>> No speech detected")
                self._notify("No speech detected")
                return

            if action == HotkeyAction.TRANSCRIBE:
                # Clean up transcription with AI
                print(">>> Cleaning up with AI...")
                self._notify("Cleaning up...")
                raw_text = text
                text = improve_transcription(text)
                print(f">>> Clean: {text}")
                print(">>> Typing...")
                self._notify(f"Typing: {text[:50]}...")
                type_text(text)
                get_history().add(raw_text, text, "transcribe")
                print(">>> Done!")

            elif action == HotkeyAction.REWRITE:
                # Get selected text and rewrite it
                selection = get_selection()
                if not selection:
                    # Try clipboard as fallback
                    selection = get_clipboard()

                if not selection:
                    self._notify("No text selected to rewrite")
                    return

                self._notify("Rewriting...")
                rewritten = rewrite(selection, text)
                self._notify(f"Typing: {rewritten[:50]}...")
                type_text(rewritten)
                get_history().add(text, rewritten, "rewrite")

            elif action == HotkeyAction.CONTEXT_REPLY:
                # Get clipboard context and generate reply
                context = get_clipboard()

                if not context:
                    self._notify("No context in clipboard")
                    return

                self._notify("Generating reply...")
                reply = context_reply(context, text)
                self._notify(f"Typing: {reply[:50]}...")
                type_text(reply)
                get_history().add(text, reply, "context_reply")

        except Exception as e:
            self._notify(f"Error: {str(e)[:50]}")
            print(f"Error processing audio: {e}")

    def _on_quit(self) -> None:
        """Handle quit from tray."""
        self._running = False
        self._hotkey_listener.stop()
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

    async def _run_hotkeys(self) -> None:
        """Run the hotkey listener."""
        self._hotkey_listener.add_callback(self._handle_hotkey)
        await self._hotkey_listener.start()

    def _run_hotkey_thread(self) -> None:
        """Run hotkey listener in a separate thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(self._run_hotkeys())
        except Exception as e:
            print(f"Hotkey listener error: {e}")
        finally:
            self._loop.close()

    def run(self) -> None:
        """Run the application."""
        print("Starting Vibe Local...")
        print()

        # Check dependencies
        deps = check_dependencies()
        missing = [name for name, available in deps.items() if not available]
        if missing:
            print(f"Missing dependencies: {', '.join(missing)}")
            print("Install with: sudo dnf install wl-clipboard")
            sys.exit(1)

        # Check input permissions
        if not check_input_permissions():
            print("You need to be in the 'input' group to capture hotkeys.")
            print("Run: sudo usermod -aG input $USER")
            print("Then log out and back in.")
            sys.exit(1)

        # Check Ollama
        if not check_ollama_available():
            print("Ollama is not running. Start it with: ollama serve")
            sys.exit(1)

        # Ensure model is available
        print("Checking Ollama model...")
        if not ensure_model_available():
            print("Failed to load Ollama model")
            sys.exit(1)

        # Print hotkey help
        print()
        print(get_hotkey_help())
        print()
        print("Ready! Look for the green mic icon in your tray.")
        print("=" * 40)

        self._running = True

        # Create tray icon
        self._tray = VibeTray(on_quit=self._on_quit)

        # Start hotkey listener in background thread
        hotkey_thread = threading.Thread(target=self._run_hotkey_thread, daemon=True)
        hotkey_thread.start()

        # Run Qt tray in main thread (required by Qt)
        self._tray.run()

        print("\nVibe Local stopped.")


def main():
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Vibe Local - Local voice-to-text with AI")
    parser.add_argument("-c", "--config", help="Path to config file")
    args = parser.parse_args()

    if args.config:
        init_config(args.config)

    app = VibeLocal()
    app.run()


if __name__ == "__main__":
    main()
