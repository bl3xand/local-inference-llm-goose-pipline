#!/bin/bash
# Install or update everything from this repository. Safe to repeat. See README.md.
set -e
cd "$(dirname "$(readlink -f "$0")")"
if [ ! -f .env ]; then
    cp example.env .env
    echo "Created .env from example.env - check the values in it (paths, memory), then run ./install.sh again if you change them."
fi
exec python3 tools/install.py "$@"
