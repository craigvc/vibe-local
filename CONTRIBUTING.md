# Contributing to Vibe Local

Thanks for your interest in contributing to Vibe Local!

## Testing

We especially need help testing on **Windows** and **macOS**. The project was developed on Linux, so cross-platform feedback is invaluable.

### How to Report Issues

1. Check if the issue already exists in [Issues](../../issues)
2. If not, open a new issue with:
   - Your operating system and version
   - Python version
   - Steps to reproduce the problem
   - Any error messages or logs

### Getting Logs

```bash
# Run vibe-local directly to see output
vibe-local

# Or check systemd logs on Linux
journalctl --user -u vibe-local -f
```

## Development

### Setting Up

```bash
git clone https://github.com/craigvc/vibe-local.git
cd vibe-local
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

### Code Style

- Follow PEP 8
- Use type hints where practical
- Keep functions focused and readable

### Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Test on your platform
5. Commit with a clear message
6. Push to your fork
7. Open a Pull Request

## Questions?

Open an issue or start a discussion. All contributions are welcome!
