#!/usr/bin/env python3
"""Put everything from this repository into place, filling in the values from .env.

  ./install.sh                 install or update (safe to repeat)
  ./install.sh --restart       also restart the model server now (interrupts a running chat)
  ./install.sh --target DIR    trial run: write into DIR instead of the home folder, touch nothing else

A file that already exists and differs is first copied to ~/.local/state/llm-pipeline-backup/<time>/.
Never enables anything at login or boot: the server runs only while Goose is open.
"""
import os, re, shutil, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import envfile

REPO = envfile.REPO
# source in the repository -> destination under the home folder, executable?
#   *.tpl files have their {{NAME}} placeholders filled in from .env
FILES = [
    ("goose/.goosehints",                    ".config/goose/.goosehints", False),
    ("goose/prompts/system.md",              ".config/goose/prompts/system.md", False),
    ("goose/prompts/compaction.md",          ".config/goose/prompts/compaction.md", False),
    ("goose/prompts/compaction_summary.md",  ".config/goose/prompts/compaction_summary.md", False),
    ("goose/prompts/subagent_system.md",     ".config/goose/prompts/subagent_system.md", False),
    ("goose/recipes/init.yaml.tpl",          ".config/goose/recipes/init.yaml", False),
    ("goose/recipes/forget.yaml.tpl",        ".config/goose/recipes/forget.yaml", False),
    ("goose/recipes/memory.yaml.tpl",        ".config/goose/recipes/memory.yaml", False),
    ("goose/environment.conf",               ".config/environment.d/goose.conf", False),
    ("goose/plugins/todo-mirror/plugin.json",       ".agents/plugins/todo-mirror/plugin.json", False),
    ("goose/plugins/todo-mirror/hooks/hooks.json",  ".agents/plugins/todo-mirror/hooks/hooks.json", False),
    ("goose/plugins/todo-mirror/scripts/mirror.py", ".agents/plugins/todo-mirror/scripts/mirror.py", True),
    ("server/models.ini.tpl",                ".config/llama-server/models.ini", False),
    ("server/llama-server.service.tpl",      ".config/systemd/user/llama-server.service", False),
    ("bin/goose-local.tpl",                  ".local/bin/goose-local", True),
    ("bin/goose-memory",                     ".local/bin/goose-memory", True),
    ("bin/goose-forget",                     ".local/bin/goose-forget", True),
    ("tools/goose-vision/server.py",         ".local/share/goose-vision/server.py", False),
    ("desktop/goose-desktop.desktop.tpl",    ".local/share/applications/goose-desktop.desktop", False),
]
GOOSE_CONFIG = (".config/goose/config.yaml", "goose/config.yaml.tpl")
CONFIG_KEYS = ["GOOSE_MODE", "GOOSE_AUTO_COMPACT_THRESHOLD", "GOOSE_MAX_TURNS", "GOOSE_SUBAGENT_MAX_TURNS", "GOOSE_THINKING_EFFORT"]


def fill(text, env, name):
    def sub(m):
        if m.group(1) not in env:
            sys.exit(f"{name}: {{{{{m.group(1)}}}}} is not set in .env or example.env")
        return env[m.group(1)]
    return re.sub(r"\{\{([A-Z_]+)\}\}", sub, text)


def models_ini(text, env):
    """Drop settings whose value is empty and apply the per-model exceptions."""
    batch = envfile.per_model(env.get("BATCH_SIZE_PER_MODEL"))
    special = {"fit-target": envfile.per_model(env.get("FIT_TARGET_PER_MODEL")), "ctx-size": envfile.per_model(env.get("CTX_SIZE_PER_MODEL")),
               "image-min-tokens": envfile.per_model(env.get("IMAGE_MIN_TOKENS_PER_MODEL")), "batch-size": batch, "ubatch-size": batch}
    present = {(m.group(1), k) for m in re.finditer(r"^\[([^\]]+)\]\n(.*?)(?=^\[|\Z)", text, flags=re.S | re.M)
               for k in re.findall(r"^([\w-]+) =", m.group(2), flags=re.M)}
    out, section = [], None
    for line in text.split("\n"):
        m = re.match(r"^\[([^\]]+)\]$", line)
        if m:
            section = m.group(1)
            out.append(line)
            # per-model settings the template has no line for go right under the section name
            out += [f"{k} = {v[section]}" for k, v in special.items() if section in v and (section, k) not in present]
            continue
        m = re.match(r"^([\w-]+) =\s*(.*)$", line)
        if m:
            if not m.group(2):
                continue
            if section in special.get(m.group(1), {}):
                line = f"{m.group(1)} = {special[m.group(1)][section]}"
        out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).rstrip("\n") + "\n"      # the same tidy-up vision-all.py does


def main():
    args = sys.argv[1:]
    trial = "--target" in args
    home = os.path.abspath(args[args.index("--target") + 1]) if trial else os.path.expanduser("~")
    env = envfile.load(home)
    backup = os.path.join(home, ".local/state/llm-pipeline-backup", time.strftime("%Y-%m-%d_%H-%M-%S"))
    changed = []

    def put(rel, text, executable=False):
        dst = os.path.join(home, rel)
        old = open(dst, encoding="utf8").read() if os.path.exists(dst) else None
        if old != text:
            if old is not None:
                os.makedirs(os.path.dirname(os.path.join(backup, rel)), exist_ok=True)
                shutil.copy2(dst, os.path.join(backup, rel))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "w", encoding="utf8").write(text)
            changed.append(("new      " if old is None else "updated  ") + rel)
        if executable:
            os.chmod(dst, 0o755)

    for src, rel, executable in FILES:
        text = open(os.path.join(REPO, src), encoding="utf8").read()
        if src.endswith(".tpl"):
            text = fill(text, env, src)
        if rel.endswith("models.ini"):
            text = models_ini(text, env)
        put(rel, text, executable)

    # goose's own settings file: goose rewrites it from its window, so an existing one is only patched
    rel, tpl = GOOSE_CONFIG
    dst = os.path.join(home, rel)
    if not os.path.exists(dst):
        put(rel, fill(open(os.path.join(REPO, tpl), encoding="utf8").read(), env, tpl))
    else:
        text = open(dst, encoding="utf8").read()
        for k in CONFIG_KEYS:
            if re.search(rf"^{k}:.*$", text, flags=re.M):
                text = re.sub(rf"^{k}:.*$", f"{k}: {env[k]}", text, flags=re.M)
            else:
                text = text.rstrip("\n") + f"\n{k}: {env[k]}\n"
        put(rel, text)

    print("\n".join(changed) if changed else "All files are already up to date.")
    if os.path.isdir(backup):
        print(f"Previous versions of the changed files: {backup}")
    if trial:
        print(f"Trial run: files are in {home}. Nothing else was touched.")
        return

    for name, hint in [(env["LLAMA_SERVER_BIN"], "llama.cpp server (build it for your GPU; set LLAMA_SERVER_BIN in .env)"),
                       ("/usr/bin/goose-desktop", "Goose Desktop"), ("magick", "ImageMagick (the image tool converts pictures with it)")]:
        if not (os.path.exists(name) or shutil.which(name)):
            print(f"MISSING: {name} - {hint}")
    if not any(f.endswith(".gguf") for f in os.listdir(env["MODELS_DIR"])) if os.path.isdir(env["MODELS_DIR"]) else True:
        print(f"NO MODELS: put *.gguf and mmproj-*.gguf files into {env['MODELS_DIR']} and run ./install.sh again")

    subprocess.run(["systemctl", "--user", "daemon-reload"])
    vision = [sys.executable, os.path.join(REPO, "tools/vision-all.py"), "--apply"] + (["--restart"] if "--restart" in args else [])
    subprocess.run(vision)
    print("\nDone. Start Goose from the 'Goose Desktop' shortcut (it starts the model server and stops it on exit).")


if __name__ == "__main__":
    main()
