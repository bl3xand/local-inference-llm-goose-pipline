#!/bin/bash
# memwatch.sh - one line every 2 seconds: VRAM, RAM held by the GPU driver, free RAM, and the loaded model's own memory.
# Read-only. Use it while tuning FIT_TARGET, CTX_SIZE or picture size in .env, or to see why the server was killed.
#
#   tools/memwatch.sh                 print to the terminal (Ctrl+C to stop)
#   tools/memwatch.sh --log FILE      also append to FILE
#   tools/memwatch.sh --guard 6000    unload the loaded model when available RAM drops under 6000 MiB
#
# Columns (MiB):
#   vram     VRAM in use on the largest card
#   gpu_ram  system RAM the GPU driver holds (GTT). A sudden jump of many GB means VRAM ran out and the driver is
#            moving the model's buffers through system RAM - leave more VRAM free (raise FIT_TARGET).
#   avail    RAM still available; near zero the kernel kills the server
#   swap     free swap
#   anon     RAM of the loaded model's process ("-" = no model loaded)
# After a kill, the kernel's own report:  journalctl -k | grep -E "gpu_active|Killed process"
cd "$(dirname "$(readlink -f "$0")")/.."
port=$(grep -hE '^LLAMA_PORT=' example.env .env 2>/dev/null | tail -1 | cut -d= -f2); port=${port:-8080}
log=""; guard=""
while [ $# -gt 0 ]; do
    case "$1" in
        --log) log="$2"; shift 2 ;;
        --guard) guard="$2"; shift 2 ;;
        *) echo "unknown option: $1"; exit 1 ;;
    esac
done
card=$(for f in /sys/class/drm/card*/device/mem_info_vram_total; do echo "$(cat "$f") $(dirname "$f")"; done 2>/dev/null | sort -n | tail -1 | cut -d" " -f2)
[ -z "$card" ] && { echo "No GPU with memory counters found (amdgpu exposes them; other drivers do not)."; exit 1; }
out() { if [ -n "$log" ]; then echo "$1" | tee -a "$log"; else echo "$1"; fi; }
out "time     vram gpu_ram avail swap | anon"
while :; do
    vram=$(( $(cat "$card/mem_info_vram_used") / 1048576 )); gtt=$(( $(cat "$card/mem_info_gtt_used") / 1048576 ))
    avail=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo); swap=$(awk '/SwapFree/{print int($2/1024)}' /proc/meminfo)
    # the router is the oldest llama-server process, a loaded model is a newer one
    anon="-"; [ "$(pgrep -c -x llama-server)" -ge 2 ] && anon=$(awk '/RssAnon/{print int($2/1024)}' "/proc/$(pgrep -n -x llama-server)/status" 2>/dev/null)
    out "$(date +%T) $vram $gtt $avail $swap | ${anon:--}"
    if [ -n "$guard" ] && [ "$avail" -lt "$guard" ] && [ "$anon" != "-" ]; then
        for m in $(curl -s "127.0.0.1:$port/models" | grep -oE '"id":"[^"]+"' | cut -d'"' -f4); do
            curl -s -X POST "127.0.0.1:$port/models/unload" -H 'Content-Type: application/json' -d "{\"model\":\"$m\"}" >/dev/null
        done
        out "$(date +%T) GUARD: available RAM $avail MiB is under $guard MiB - models unloaded"
    fi
    sleep 2
done
