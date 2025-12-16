#!/bin/bash
# Launch Vibe Local
cd "$(dirname "$0")"
source venv/bin/activate
python -m vibe_local "$@"
