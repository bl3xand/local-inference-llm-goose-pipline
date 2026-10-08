#!/bin/bash
# Goose Desktop + local LLM: the model server lives only while Goose is open.
set -a; . "$HOME/.config/environment.d/goose.conf"; set +a
# make the helper commands (goose-memory, goose-forget) visible to the shell inside Goose
export PATH="$HOME/.local/bin:$PATH"
# keep goose's model catalog knowing our local models (picture input, reasoning switch); cheap and idempotent
V="{{REPO_DIR}}/tools/vision-all.py"; [ -f "$V" ] && python3 "$V" --apply >/dev/null 2>&1
systemctl --user start llama-server.service
/usr/bin/goose-desktop "$@"
# Still running in another window or a goose CLI session? Then leave the server up.
pgrep -f '^/opt/goose-desktop/Goose' >/dev/null || pgrep -x goose >/dev/null && exit 0
systemctl --user stop llama-server.service
