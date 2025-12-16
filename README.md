# Vibe Local

Local voice-to-text with AI-powered text cleanup. A privacy-focused alternative to cloud-based voice typing services.

> **Looking for Testers!** This project has been developed and tested on Linux only. If you're on **Windows** or **macOS** and would like to help test, please give it a try and [open an issue](../../issues) with any problems you encounter. Your feedback is greatly appreciated!

## Features

- **Voice-to-text**: Hold a hotkey, speak, release to type transcribed text
- **AI Rewrite**: Select text, hold hotkey, describe how you want it rewritten
- **Context Reply**: Copy a conversation to clipboard, hold hotkey, speak your intent to generate a reply
- **Fully Local**: All processing happens on your machine using Whisper and Ollama

## Requirements

- Python 3.10+
- [Ollama](https://ollama.ai/) running locally with a model (default: llama3.2)
- CUDA-capable GPU recommended for fast transcription

### Platform-Specific Requirements

**Linux (Wayland/KDE):**
- `ydotool` for text input simulation
- `wl-clipboard` for clipboard access (Wayland)

**Linux (X11):**
- `xclip` for clipboard access

**Windows:**
- No additional requirements

**macOS:**
- Grant Accessibility permissions when prompted

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/vibe-local.git
cd vibe-local

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -e .

# Install Ollama and pull a model
# See https://ollama.ai for installation
ollama pull llama3.2
```

### Linux Setup

Install ydotool for text input:

```bash
# Fedora/Nobara
sudo dnf install ydotool

# Ubuntu/Debian
sudo apt install ydotool

# Start ydotool daemon
sudo systemctl enable --now ydotool
```

## Configuration

Edit `config.yaml` to customize:

```yaml
# Hotkeys (evdev key names)
hotkeys:
  transcribe: ["KEY_LEFTCTRL", "KEY_LEFTSHIFT"]      # Ctrl+Shift
  rewrite: ["KEY_LEFTMETA", "KEY_LEFTSHIFT", "KEY_R"] # Super+Shift+R
  context_reply: ["KEY_LEFTMETA", "KEY_LEFTSHIFT", "KEY_C"] # Super+Shift+C

# Whisper settings
whisper:
  model: "medium"        # tiny, base, small, medium, large-v3
  language: "en"         # Language code or "auto"
  device: "cuda"         # cuda or cpu
  compute_type: "float16"

# Ollama settings
ollama:
  model: "llama3.2"
  base_url: "http://localhost:11434"

# Writing style: formal, casual, very_casual
style: "casual"
```

## Usage

```bash
# Run directly
vibe-local

# Or with Python
python -m vibe_local.main
```

### Hotkeys

| Action | Default Hotkey | Description |
|--------|----------------|-------------|
| Voice-to-text | Ctrl+Shift (hold) | Speak while holding, releases types the text |
| Rewrite | Super+Shift+R (hold) | Select text first, then speak how to rewrite it |
| Context Reply | Super+Shift+C (hold) | Copy conversation to clipboard, then speak your intent |

### Running as a Service (Linux)

Create `~/.config/systemd/user/vibe-local.service`:

```ini
[Unit]
Description=Vibe Local - Voice-to-text with AI
After=graphical-session.target

[Service]
Type=simple
ExecStart=/path/to/vibe-local/venv/bin/vibe-local
WorkingDirectory=/path/to/vibe-local
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

Enable and start:

```bash
systemctl --user enable --now vibe-local
```

## Troubleshooting

### Text not typing (Linux/Wayland)

Ensure ydotool is installed and the daemon is running:

```bash
sudo systemctl status ydotool
```

### Hotkeys not detected

On macOS, grant Accessibility permissions in System Preferences > Security & Privacy > Privacy > Accessibility.

On Linux, you may need to add your user to the `input` group:

```bash
sudo usermod -aG input $USER
# Log out and back in
```

### Slow transcription

- Use a smaller Whisper model (`tiny` or `base`)
- Ensure CUDA is available: set `device: "cuda"` in config
- Use `compute_type: "int8"` for faster inference

## License

MIT
