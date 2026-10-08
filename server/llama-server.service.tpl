[Unit]
Description=llama.cpp server (local models, 127.0.0.1 only)
# No [Install] section on purpose: this unit is never started at login/boot.
# It is started by ~/.local/bin/goose-local (the Goose Desktop launcher) or by hand.

[Service]
# Router mode: models are defined in models.ini, loaded on first request, one at a time,
# and unloaded from VRAM after SLEEP_IDLE_SECONDS without requests.
ExecStart={{LLAMA_SERVER_BIN}} \
    --host {{LLAMA_HOST}} --port {{LLAMA_PORT}} \
    --models-preset %h/.config/llama-server/models.ini --models-max 1 \
    --sleep-idle-seconds {{SLEEP_IDLE_SECONDS}}
Restart=on-failure
RestartSec=5
