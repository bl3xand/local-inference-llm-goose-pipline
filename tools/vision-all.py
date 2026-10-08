#!/usr/bin/env python3
"""vision-all.py - make every model in the models folder (MODELS_DIR in .env) a first-class model in goose, under its normal name:
picture input (also for images pasted into the chat), a working "reasoning effort" switch, and a complete
catalog card (name, description, family, dates, context, output limit) as if goose had downloaded it itself.

WHY IT IS NEEDED
goose decides what a model can do from its model catalog and finds a model there by provider + model name.
A local model served by llama.cpp is not in that catalog, so goose
  - drops pasted images ("[image omitted: model does not support vision]"),
  - shows no reasoning switch, or shows one that changes nothing.

HOW IT WORKS (three facts about goose 1.53, found in its source)
 1. Catalog. At start goose loads ~/.local/share/goose/model_catalog/models_dev_api.json and then tries to
    replace it with a fresh download from models.dev. We add our models to that file and make the FOLDER
    read-only: the download cannot be written, goose logs a warning and keeps our file.
    Price: the catalog of cloud models is frozen until `--update-catalog`.
 2. Reasoning level. For an OpenAI-compatible server goose sends the level chosen in the UI
    (`reasoning_effort`) only if the provider's internal name is on a short built-in list. The only name on it
    is "meta", so our provider file is called meta.json and has "name": "meta" (it replaces goose's built-in
    Meta provider, which needs a paid key anyway). In the UI it is still shown as "llama.cpp (local)".
    goose maps the UI levels to: Off -> low, Low -> low, Medium -> medium, High -> high, Max -> xhigh.
 3. Chat template. llama.cpp hands `reasoning_effort` to the model's chat template. Our templates get a small
    header that turns the level into one sentence at the end of the system prompt (low = think briefly,
    high / xhigh = think carefully). A second header switches reasoning off when the system prompt contains
    "/no_think" - that is how goose subagents run without reasoning.

WHAT IT KEEPS IN STEP WITH THE MODELS FOLDER
  ~/.config/llama-server/models.ini            one [section] per *.gguf; the section name is the model's name
  ~/.config/llama-server/templates/NAME.jinja  the model's own chat template + the two headers above
  ~/.config/goose/custom_providers/meta.json   the model list goose shows
  ~/.local/share/goose/model_catalog/models_dev_api.json   the catalog cards
A new *.gguf gets all four; a deleted one loses them. A new model's section starts with CTX_SIZE and FIT_TARGET
from .env; to give it hand-tuned settings that survive ./install.sh, add its section to server/models.ini.tpl. A model without a projector file (mmproj-*.gguf) cannot
see images at all: it is listed as text-only.

USAGE
  python3 vision-all.py                    show the table, change nothing
  python3 vision-all.py --apply            write everything, then restart Goose from its launcher
  python3 vision-all.py --apply --restart  also restart the model server now (interrupts a running chat)
  python3 vision-all.py --update-catalog   download a fresh catalog from models.dev and re-add our models
  python3 vision-all.py --undo             remove our catalog cards and let goose update its catalog again
The Goose launcher (~/.local/bin/goose-local) runs `--apply` at every start, so a new file is picked up by itself.
"""
import json, os, re, struct, subprocess, sys, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import envfile

ENV = envfile.load()
HOME = os.path.expanduser("~")
MODELS = ENV["MODELS_DIR"]
SERVER = f"http://{ENV['LLAMA_HOST']}:{ENV['LLAMA_PORT']}"
INI = f"{HOME}/.config/llama-server/models.ini"
TEMPLATES = f"{HOME}/.config/llama-server/templates"
PROVIDER_DIR = f"{HOME}/.config/goose/custom_providers"
PROVIDER_NAME = "meta"                 # see fact 2 above: the only provider name for which goose forwards the level
OLD_PROVIDER_NAMES = ["nano-gpt"]
GOOSE_CONFIG = f"{HOME}/.config/goose/config.yaml"
CATALOG_DIR = f"{HOME}/.local/share/goose/model_catalog"
CATALOG = f"{CATALOG_DIR}/models_dev_api.json"
CATALOG_URL = "https://models.dev/api.json"
MARK = "vision-all.py"                 # our catalog cards carry this in "local_note"
OUTPUT_LIMIT = int(ENV["OUTPUT_LIMIT"])  # goose sends it as max_tokens: the longest single reply
BAD_NAME = re.compile(r"(?i)(?:^|[-/])(?:o\d+(?:$|-)|gpt-(?:5|6)(?:$|[-.]))|-latest$|-\d{4}$|-\d{8}$|-bedrock$")

HEADER_BEGIN = "{#- ==== local headers added by vision-all.py (the model's own template follows) ==== -#}\n"
HEADER_END = "{#- ==== end of local headers ==== -#}\n"
HEADERS = HEADER_BEGIN + r"""{#- 1. a system prompt containing /no_think switches reasoning off for this request (goose subagents) -#}
{%- set _no_think = messages and messages[0].role in ['system', 'developer'] and messages[0].content is string and '/no_think' in messages[0].content %}
{%- if _no_think %}
    {%- set enable_thinking = false %}
{%- endif %}
{#- 2. the reasoning level chosen in goose becomes one sentence at the end of the system prompt -#}
{%- set _eff = reasoning_effort | default('') %}
{%- set _note = '' %}
{%- if _eff == 'low' %}
    {%- set _note = 'Reasoning effort is set to low. Keep your thinking brief and focused: decide and act, no long deliberation.' %}
{%- elif _eff == 'high' %}
    {%- set _note = 'Reasoning effort is set to high. Think the task through before acting and check your key assumptions.' %}
{%- elif _eff == 'xhigh' or _eff == 'max' %}
    {%- set _note = 'Reasoning effort is set to maximum. Think very carefully: validate key assumptions, consider plausible alternatives, and prioritise correctness over speed.' %}
{%- endif %}
{%- if _note and not _no_think and messages and messages[0].role in ['system', 'developer'] and messages[0].content is string %}
    {%- set messages = [{'role': messages[0].role, 'content': messages[0].content ~ '\n\n' ~ _note}] + messages[1:] %}
{%- endif %}
""" + HEADER_END

# What we know about the models in use. Anything not listed here is described from the GGUF file itself.
KNOWN = [
    ("ornith-1.5-35b", dict(name="Ornith 1.5 35B-A3B", family="ornith", release="2026-08-18",
                            about="Open-weight mixture-of-experts model (35B total, about 3B active) for agentic coding, tool use and image understanding.")),
    ("cyber-tiel-coder", dict(name="Cyber-Tiel-Coder 35B-A3B (uncensored)", family="ornith", release="2026-08-31",
                              about="Ornith 1.5 35B with refusals removed, re-quantized for coding and security work; built-in MTP head.")),
    ("tiel-coder", dict(name="Tiel-Coder 35B-A3B", family="ornith", release="2026-08-24",
                        about="Ornith 1.5 35B re-quantized for coding with the Sharp chat template; built-in MTP head.")),
    ("occamy", dict(name="Occamy 1.0 35B-A3B", family="qwen", release="2026-09-15",
                    about="Qwen3.6-35B-A3B post-trained by Accio-Lab for long multi-step work with tools, files and search.")),
    ("qwen3.8-35b-a3b-distill", dict(name="Qwen3.8 35B-A3B Distill", family="qwen", release="2026-09-16",
                                     about="Distillation of the Qwen3.8 frontier models into the Qwen3.6-35B-A3B mixture-of-experts architecture.")),
    ("gemma-4-26b", dict(name="Gemma 4 26B-A4B", family="gemma", release="2026-04-01",
                         about="Google's mixture-of-experts Gemma 4 (26B total, about 4B active) with image input.")),
]


def gguf_meta(path, limit=96_000_000):
    """Scalar metadata of a GGUF file (strings and numbers); arrays are skipped."""
    out = {}
    try:
        buf = open(path, "rb").read(limit)
        if buf[:4] != b"GGUF":
            return out
        pos = 8
        _tensors, n_kv = struct.unpack_from("<QQ", buf, pos)
        pos += 16
        size = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
        fmt = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}

        def string(p):
            n = struct.unpack_from("<Q", buf, p)[0]
            return buf[p + 8:p + 8 + n].decode("utf8", "replace"), p + 8 + n

        for _ in range(n_kv):
            key, pos = string(pos)
            t = struct.unpack_from("<I", buf, pos)[0]
            pos += 4
            if t == 8:
                out[key], pos = string(pos)
            elif t == 9:
                et, n = struct.unpack_from("<IQ", buf, pos)
                pos += 12
                if et == 8:
                    for _ in range(n):
                        pos += 8 + struct.unpack_from("<Q", buf, pos)[0]
                else:
                    pos += size[et] * n
            else:
                out[key] = struct.unpack_from(fmt[t], buf, pos)[0]
                pos += size[t]
    except Exception:
        pass
    return out


def sections(text):
    return [(m.group(1), m.group(2)) for m in re.finditer(r"^\[([^\]]+)\]\n(.*?)(?=^\[|\Z)", text, flags=re.S | re.M)]


def get(body, key):
    m = re.search(rf"^{re.escape(key)}\s*=\s*(.*)$", body, flags=re.M)
    return m.group(1).strip() if m else None


def find_mmproj(model_file, known):
    if known and os.path.exists(known):
        return known
    name, best, score = model_file.lower(), None, 0
    for p in os.listdir(MODELS):
        if not (p.lower().startswith("mmproj") and p.endswith(".gguf")):
            continue
        tokens = [t for t in re.split(r"[-_.]", p.lower()) if t and t not in ("mmproj", "gguf", "bf16", "f16", "f32", "a3b", "a4b")]
        s = sum(len(t) for t in tokens if t in name)
        if s > score:
            best, score = p, s
    return os.path.join(MODELS, best) if best and score >= 4 else None


def card(p):
    """The catalog card of one model, in the models.dev format goose reads."""
    f, meta = p["file"], p["meta"]
    known = next((v for k, v in KNOWN if k in f.lower()), None)
    m = re.search(r"(?i)[-.]((?:UD-)?I?Q\d\w*|BF16|F16)\.gguf$", f)
    quant = m.group(1) if m else ""
    base = known["name"] if known else (meta.get("general.name") or re.sub(r"\.gguf$", "", f))
    size_gb = os.path.getsize(p["path"]) / 1e9
    released = known["release"] if known else time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(p["path"])))
    about = known["about"] if known else f"Local model {meta.get('general.name', f)} ({meta.get('general.architecture', 'unknown architecture')})."
    trained_ctx = next((v for k, v in meta.items() if k.endswith(".context_length")), None)
    vision = bool(p["mmproj"])
    return {
        "id": p["section"],
        "name": f"{base}{' ' + quant if quant else ''} (local)",
        "description": f"{about} Runs locally on llama.cpp from {f} ({size_gb:.1f} GB); window {p['ctx']} tokens"
                       + (f", trained for {trained_ctx}" if trained_ctx else "") + ("; sees images." if vision else "; text only: no projector file."),
        "local_note": MARK,
        "family": known["family"] if known else (meta.get("general.basename") or meta.get("general.architecture") or "local"),
        "attachment": vision,
        "reasoning": True,
        "reasoning_options": [],
        "tool_call": True,
        "structured_output": True,
        "temperature": True,
        "release_date": released,
        "last_updated": time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(p["path"]))),
        "modalities": {"input": ["text", "image"] if vision else ["text"], "output": ["text"]},
        "open_weights": True,
        "limit": {"context": p["ctx"], "input": p["ctx"], "output": OUTPUT_LIMIT},
        "cost": {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0},
    }


def writable(flag):
    os.chmod(CATALOG_DIR, 0o755 if flag else 0o555)


def strip_ours(cat):
    for prov in cat.values():
        models = prov.get("models") if isinstance(prov, dict) else None
        if isinstance(models, dict):
            for k in [k for k, v in models.items() if isinstance(v, dict) and (v.get("local_note") == MARK or MARK in str(v.get("description", "")))]:
                del models[k]


def main():
    args = set(sys.argv[1:])
    if "--undo" in args:
        cat = json.load(open(CATALOG))
        strip_ours(cat)
        writable(True)
        json.dump(cat, open(CATALOG, "w"), ensure_ascii=False)
        print("Our catalog cards are removed and goose may update its catalog again.\n"
              "Pasted images and the reasoning switch stop working for local models until the next --apply.")
        return

    if not os.path.exists(INI) or not os.path.isdir(MODELS):
        sys.exit(f"Missing {INI if not os.path.exists(INI) else MODELS}. Run ./install.sh in {envfile.REPO} first.")
    ini = open(INI).read()
    secs = sections(ini)
    by_model = {os.path.basename(get(b, "model") or ""): (n, b) for n, b in secs if n != "*"}
    taken = {n for n, _ in secs}
    plan, notes = [], []
    for f in sorted(x for x in os.listdir(MODELS) if x.endswith(".gguf") and not x.lower().startswith("mmproj")):
        sec, body = by_model.get(f, (None, ""))
        new = sec is None
        if new:
            sec = re.sub(r"[^a-z0-9.]+", "-", re.sub(r"\.gguf$", "", f.lower())).strip("-")[:40].strip("-")
            while BAD_NAME.search(sec) or sec in taken:
                sec += "-local"
            taken.add(sec)
        path = os.path.join(MODELS, f)
        mm = find_mmproj(f, get(body, "mmproj"))
        if not mm:
            notes.append(f"TEXT ONLY: {f} has no projector file (mmproj-*.gguf) in models/ - it cannot see images")
        plan.append(dict(file=f, path=path, section=sec, body=body, mmproj=mm, new=new, meta=gguf_meta(path),
                         ctx=int(get(body, "ctx-size") or ENV["CTX_SIZE"])))
    stale = [n for n, b in secs if n != "*" and not os.path.exists(get(b, "model") or "")]

    print(f"{'model file':48} {'name in goose':24} {'pictures':9} {'catalog name':44} status")
    for p in plan:
        p["card"] = card(p)
        print(f"{p['file']:48} {p['section']:24} {'yes' if p['mmproj'] else 'NO':9} {p['card']['name']:44} {'NEW' if p['new'] else 'ok'}")
    for n in stale:
        print(f"{'(file is gone)':48} {n:24} {'':9} {'':44} REMOVE")
    for x in notes:
        print(x)

    if "--update-catalog" in args:
        writable(True)
        if os.path.exists(f"{CATALOG_DIR}/models_dev_api.etag"):
            os.remove(f"{CATALOG_DIR}/models_dev_api.etag")
        data = urllib.request.urlopen(urllib.request.Request(CATALOG_URL, headers={"User-Agent": "goose/model-catalog"}), timeout=60).read()
        json.loads(data)                                    # refuse to store something that is not JSON
        open(CATALOG, "wb").write(data)
        print("\nFresh catalog downloaded from models.dev.")
        args.add("--apply")
    if "--apply" not in args:
        print("\nNothing written. Run with --apply to write the changes.")
        return

    # ---- chat templates: the model's own template with our two headers in front
    os.makedirs(TEMPLATES, exist_ok=True)
    os.makedirs(PROVIDER_DIR, exist_ok=True)
    for p in plan:
        tmpl = p["meta"].get("tokenizer.chat_template")
        p["template"] = None
        if tmpl and "enable_thinking" in tmpl:
            p["template"] = f"{TEMPLATES}/{p['section']}.jinja"
            open(p["template"], "w").write(HEADERS + tmpl)
        elif tmpl is None and get(p["body"], "chat-template-file"):
            p["template"] = get(p["body"], "chat-template-file")      # could not read the file's template: keep what is there

    # ---- models.ini
    for n in stale:
        ini = re.sub(rf"^\[{re.escape(n)}\]\n.*?(?=^\[|\Z)", "", ini, flags=re.S | re.M)
        if os.path.exists(f"{TEMPLATES}/{n}.jinja"):
            os.remove(f"{TEMPLATES}/{n}.jinja")
    for p in plan:
        if p["new"]:
            lines = [f"[{p['section']}]", f"model = {p['path']}"]
            if p["mmproj"]:
                lines.append(f"mmproj = {p['mmproj']}")
            if p["template"]:
                lines.append(f"chat-template-file = {p['template']}")
            lines += [f"ctx-size = {envfile.per_model(ENV.get('CTX_SIZE_PER_MODEL')).get(p['section'], ENV['CTX_SIZE'])}",
                      f"fit-target = {envfile.per_model(ENV.get('FIT_TARGET_PER_MODEL')).get(p['section'], ENV['FIT_TARGET'])}"]
            ini = ini.rstrip("\n") + "\n\n" + "\n".join(lines) + "\n"
        else:
            keep = [l for l in p["body"].split("\n") if not l.startswith(("alias =", "chat-template-file =")) and "catalog marks as vision-capable" not in l]
            head = ([f"mmproj = {p['mmproj']}"] if p["mmproj"] and get(p["body"], "mmproj") is None else [])
            head += [f"chat-template-file = {p['template']}"] if p["template"] else []
            ini = ini.replace(f"[{p['section']}]\n{p['body']}", f"[{p['section']}]\n" + "\n".join(head + keep), 1)
    open(INI, "w").write(re.sub(r"\n{3,}", "\n\n", ini).rstrip("\n") + "\n")

    # ---- goose provider file
    target = f"{PROVIDER_DIR}/{PROVIDER_NAME}.json"
    source = next((x for x in [target] + [f"{PROVIDER_DIR}/{n}.json" for n in OLD_PROVIDER_NAMES] if os.path.exists(x)), None)
    prov = json.load(open(source)) if source else {"engine": "openai", "api_key_env": "", "requires_auth": False, "supports_streaming": True,
                                                    "base_url": ""}
    prov.update(name=PROVIDER_NAME, base_url=f"{SERVER}/v1/chat/completions", display_name="llama.cpp (local)", catalog_provider_id=PROVIDER_NAME,
                description=f"Local llama-server on {ENV['LLAMA_HOST']}:{ENV['LLAMA_PORT']}. Model names are the section names of ~/.config/llama-server/models.ini. "
                            "The internal provider name 'meta' is deliberate: it is the only name for which goose forwards the reasoning "
                            "level to an OpenAI-compatible server. Everything here is maintained by tools/vision-all.py of the pipeline repository.",
                models=[{"name": p["section"], "context_limit": p["ctx"], "max_tokens": OUTPUT_LIMIT, "reasoning": True,
                         "input_token_cost": 0.0, "output_token_cost": 0.0, "currency": "USD"} for p in plan])
    json.dump(prov, open(target, "w"), indent=2, ensure_ascii=False)
    for n in OLD_PROVIDER_NAMES:
        if os.path.exists(f"{PROVIDER_DIR}/{n}.json"):
            os.remove(f"{PROVIDER_DIR}/{n}.json")

    # ---- catalog (goose creates the file at its first start)
    if os.path.exists(CATALOG):
        cat = json.load(open(CATALOG))
        strip_ours(cat)
        block = cat.setdefault(PROVIDER_NAME, {"id": PROVIDER_NAME, "name": "llama.cpp (local)", "models": {}})
        block.setdefault("models", {})
        for p in plan:
            block["models"][p["section"]] = p["card"]
        writable(True)
        json.dump(cat, open(CATALOG, "w"), ensure_ascii=False)
        writable(False)
    else:
        print("\nNOTE: goose has no model catalog yet. Start Goose once, close it and start it again: the launcher repeats this step.")

    # ---- goose config: provider name and, if needed, the selected model
    cfg = open(GOOSE_CONFIG).read() if os.path.exists(GOOSE_CONFIG) else ""
    new_cfg = cfg
    for n in OLD_PROVIDER_NAMES:
        new_cfg = re.sub(rf"^(\s+){re.escape(n)}:\s*$", rf"\g<1>{PROVIDER_NAME}:", new_cfg, flags=re.M)
        new_cfg = re.sub(rf"^(active_provider:\s*){re.escape(n)}\s*$", rf"\g<1>{PROVIDER_NAME}", new_cfg, flags=re.M)
    names = [p["section"] for p in plan]
    m = re.search(r"^(\s+model:\s*)(\S+)\s*$", new_cfg, flags=re.M)
    if m and m.group(2) not in names and names:
        new_cfg = new_cfg[:m.start(2)] + names[0] + new_cfg[m.end(2):]
        print(f"\nThe selected model '{m.group(2)}' no longer exists: goose now starts with '{names[0]}'.")
    if new_cfg != cfg and cfg:
        open(GOOSE_CONFIG, "w").write(new_cfg)

    print(f"\nWritten: {INI}\n         {TEMPLATES}/*.jinja\n         {target}\n         {CATALOG}  (its folder is read-only on purpose)")
    if "--restart" in args:
        subprocess.run(["systemctl", "--user", "restart", "llama-server.service"])
        print("Model server restarted. Restart Goose to load the new list and catalog.")
    else:
        print("Restart Goose from its launcher: that reloads the list, the catalog and the model server.")


if __name__ == "__main__":
    main()
