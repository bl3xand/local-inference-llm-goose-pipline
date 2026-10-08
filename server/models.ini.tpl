; Models served by llama-server.service (router mode, one model in VRAM at a time).
; GENERATED from server/models.ini.tpl + .env by install.sh - edit those, not this file.
;
; VRAM SAFETY: the desktop shares the card with the model. "fit-target" is the VRAM (MiB) llama.cpp keeps free when it splits
; a model between VRAM and RAM (FIT_TARGET / FIT_TARGET_PER_MODEL in .env). On a 16 GB card 830 leaves about 0.1 GB free.
; If VRAM runs out completely gnome-shell cannot allocate framebuffers and the session crashes - raise it then.

[*]
device = {{DEVICE}}
cache-type-k = {{KV_CACHE_TYPE}}
cache-type-v = {{KV_CACHE_TYPE}}
flash-attn = on
cache-reuse = 256
; Load weights into memory instead of mmap: only the CPU-side part stays in RAM.
load-mode = none
cache-ram = {{CACHE_RAM}}
; -1 = no cap on thinking: a reply may reason for as long as the context window allows.
; If a model loops in its reasoning, stop it with the Stop button; to limit it set REASONING_BUDGET, e.g. 8192
reasoning-budget = {{REASONING_BUDGET}}
; Pictures. MMPROJ_DEVICE empty = the picture encoder runs on the GPU; "none" = on the CPU (slow, but needs no VRAM).
; IMAGE_MIN_TOKENS empty = the server's default (small) picture size. Large pictures (4096 / 1120 tokens) encoded on the GPU
; with ~0.1 GB of free VRAM ran out of VRAM and crashed gnome-shell twice on 2026-10-07: raise it only together with
; MMPROJ_DEVICE=none or a larger FIT_TARGET. A line whose value is empty is left out of the generated file.
mmproj-device = {{MMPROJ_DEVICE}}
image-min-tokens = {{IMAGE_MIN_TOKENS}}
threads-batch = {{THREADS_BATCH}}
; request streams sharing one context pool: the main agent plus subagents on one loaded model
parallel = {{PARALLEL}}
kv-unified = true

; MoE 35B (3B active): expert weights that do not fit go to RAM. Default model.
[ornith-1.5-35b]
chat-template-file = {{HOME}}/.config/llama-server/templates/ornith-1.5-35b.jinja
model = {{MODELS_DIR}}/Ornith-1.5-35B-Q4_K_M.gguf
mmproj = {{MODELS_DIR}}/mmproj-Ornith-1.5-35B-BF16.gguf
ctx-size = {{CTX_SIZE}}
fit-target = {{FIT_TARGET}}
; sampling recommended on the Ornith model card for coding
temp = 0.6
top-p = 0.95
top-k = 20
min-p = 0

[distill-35b]
chat-template-file = {{HOME}}/.config/llama-server/templates/distill-35b.jinja
model = {{MODELS_DIR}}/Qwen3.8-35B-A3B-Distill-Q4_K_M.gguf
mmproj = {{MODELS_DIR}}/mmproj-Qwen3.8-35B-A3B-F16.gguf
ctx-size = {{CTX_SIZE}}
fit-target = {{FIT_TARGET}}
; sampling recommended on the model card (temperature 0.6, top_p 0.95, top_k 20)
temp = 0.6
top-p = 0.95
top-k = 20
min-p = 0

[occamy-35b]
chat-template-file = {{HOME}}/.config/llama-server/templates/occamy-35b.jinja
model = {{MODELS_DIR}}/occamy-1.0-Q4_K_M.gguf
mmproj = {{MODELS_DIR}}/mmproj-occamy-1.0-F16.gguf
ctx-size = {{CTX_SIZE}}
fit-target = {{FIT_TARGET}}
; sampling recommended on the Occamy card: temp 1.0, top_p 0.95, top_k 20. The card also lists presence_penalty 1.5,
; left off: it penalises repeating tokens, which code needs, and the authors say it is unproven for coding
temp = 1.0
top-p = 0.95
top-k = 20
min-p = 0

[cyber-tiel-35b]
chat-template-file = {{HOME}}/.config/llama-server/templates/cyber-tiel-35b.jinja
model = {{MODELS_DIR}}/Cyber-Tiel-Coder-35B-A3B-MTP-UD-Q4_K_XL.gguf
mmproj = {{MODELS_DIR}}/mmproj-Cyber-Tiel-Coder-35B-A3B-BF16.gguf
ctx-size = {{CTX_SIZE}}
fit-target = {{FIT_TARGET}}
; sampling recommended on the Cyber-Tiel card for coding: temp 0.6, top_p 0.95, top_k 20, min_p 0
temp = 0.6
top-p = 0.95
top-k = 20
min-p = 0

[tiel-coder-35b]
chat-template-file = {{HOME}}/.config/llama-server/templates/tiel-coder-35b.jinja
model = {{MODELS_DIR}}/Tiel-Coder-35B-A3B-MTP-UD-Q4_K_XL.gguf
mmproj = {{MODELS_DIR}}/mmproj-Tiel-Coder-35B-A3B-BF16.gguf
ctx-size = {{CTX_SIZE}}
fit-target = {{FIT_TARGET}}
; sampling recommended on the Tiel card for agentic coding (general chat would be temp 1.0)
temp = 0.6
top-p = 0.95
top-k = 20
min-p = 0

[gemma-4-26b]
chat-template-file = {{HOME}}/.config/llama-server/templates/gemma-4-26b.jinja
model = {{MODELS_DIR}}/gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf
mmproj = {{MODELS_DIR}}/mmproj-gemma-4-26B-A4B-BF16.gguf
ctx-size = {{CTX_SIZE}}
fit-target = {{FIT_TARGET}}
; sampling recommended by Google for Gemma 4 (llama.cpp defaults are colder and loop more easily)
temp = 1.0
top-p = 0.95
top-k = 64
; Gemma 4 has a known habit of looping inside its reasoning (google-deepmind/gemma issue 727, Google AI forum).
; Community workaround that reduces it: a mild repeat penalty over a long window.
repeat-penalty = 1.08
repeat-last-n = 4096

[gemma-4-26b-q6]
chat-template-file = {{HOME}}/.config/llama-server/templates/gemma-4-26b-q6.jinja
model = {{MODELS_DIR}}/gemma-4-26B-A4B-it-UD-Q6_K.gguf
mmproj = {{MODELS_DIR}}/mmproj-gemma-4-26B-A4B-BF16.gguf
ctx-size = {{CTX_SIZE}}
; This model gets ~0.5 GB of free VRAM (FIT_TARGET_PER_MODEL in .env, 1230) instead of ~0.1 GB. With 0.1 GB the desktop's next VRAM request made the
; driver move ~12 GB of the model's buffers through system RAM for a second; Gemma leaves too little RAM for that and the
; kernel killed the server (5 times on 2026-10-07/08). If it happens again raise this further (2048 = ~1.3 GB free).
fit-target = {{FIT_TARGET}}
; sampling recommended by Google for Gemma 4 (llama.cpp defaults are colder and loop more easily)
temp = 1.0
top-p = 0.95
top-k = 64
; Gemma 4 has a known habit of looping inside its reasoning (google-deepmind/gemma issue 727, Google AI forum).
; Community workaround that reduces it: a mild repeat penalty over a long window.
repeat-penalty = 1.08
repeat-last-n = 4096

