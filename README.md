# Local "Claude Code": Goose + llama.cpp

Settings, rules and scripts that make Goose Desktop work with local models served by `llama-server`.
The model server starts together with Goose and stops when Goose is closed; nothing is added to autostart.

## Installing on a new computer

1. Install separately: Goose Desktop, `llama-server` (llama.cpp built for your GPU), Python 3, ImageMagick.
2. Clone the repository and run the installer:

   ```bash
   git clone https://github.com/bl3xand/local-inference-llm-goose-pipline.git
   cd local-inference-llm-goose-pipline
   ./install.sh
   ```

   The first run creates `.env` from `example.env`.
3. Check `.env` (paths, memory, GPU) and put the models into `models/`, or point `MODELS_DIR` at your own folder.
4. Run `./install.sh` again, then open Goose with the "Goose Desktop" shortcut.
5. If models do not see pasted pictures: close Goose and open it again (Goose creates its model catalog on first start).

## Changing settings

Every number that needs tuning lives in `.env`: free VRAM margin, context window, threads, picture size, reasoning cap,
compaction threshold. Each one is described in `example.env`.

```bash
./install.sh
```

The command is safe to repeat: it rewrites only the files that changed and keeps their previous versions in
`~/.local/state/llm-pipeline-backup/`. With `--restart` it also restarts the model server at once (this interrupts a
running chat). Without it, new server settings take effect the next time Goose is opened.

To see the result without touching anything:

```bash
./install.sh --target /tmp/trial
```

The files in the home folder are derived copies. Edit the files here, otherwise the next `./install.sh` puts the copies
back to what the repository says. The exception is `~/.config/goose/config.yaml`: Goose maintains it itself, and the
installer changes only five values in it, taken from `.env`.

## Structure

| Path | What it is | Installed to |
|---|---|---|
| `example.env` | all settings with descriptions; your copy `.env` is not in git | - |
| `install.sh`, `tools/install.py` | the installer | - |
| `goose/.goosehints` | rules for the models | `~/.config/goose/.goosehints` |
| `goose/prompts/` | system prompt, context compaction, subagents | `~/.config/goose/prompts/` |
| `goose/environment.conf` | the reminder Goose adds to every turn | `~/.config/environment.d/goose.conf` |
| `goose/recipes/` | the `/init`, `/memory`, `/forget` commands | `~/.config/goose/recipes/` |
| `goose/plugins/todo-mirror/` | copies the plan into memory on every change | `~/.agents/plugins/todo-mirror/` |
| `goose/config.yaml.tpl` | Goose settings for a first install | `~/.config/goose/config.yaml` |
| `server/models.ini.tpl` | per-model server settings | `~/.config/llama-server/models.ini` |
| `server/llama-server.service.tpl` | the server unit (no autostart) | `~/.config/systemd/user/` |
| `bin/goose-local.tpl` | starts Goose together with the server | `~/.local/bin/goose-local` |
| `bin/goose-memory`, `bin/goose-forget` | clean up memory and chat history | `~/.local/bin/` |
| `desktop/` | the "Goose Desktop" shortcut | `~/.local/share/applications/` |
| `tools/vision-all.py` | makes every model in the folder first-class in Goose: name, pictures, reasoning levels | runs in place |
| `tools/goose-vision/` | the "look at an image file" tool | `~/.local/share/goose-vision/` |
| `tools/envfile.py` | reads `.env` | - |
| `models/` | put the models here; the files themselves are not in git | - |
| `docs/command.md` | command cheat sheet | - |

## Adding a model

Put the `.gguf` and its `mmproj-*.gguf` into the models folder and reopen Goose: the model appears in the list by itself,
with the window and VRAM margin from `.env`. To give a model its own parameters (temperature and so on) that survive
`./install.sh`, add its section to `server/models.ini.tpl`, following the neighbouring ones.

## What is not here

- The models, model memory, chat history, keys and login data.
- Installing Goose, llama.cpp and drivers.
- Tuning for other hardware: the values in `example.env` were found by measurement on an RX 9070 XT 16 GB with 32 GB of RAM.

After a Goose update, compare `goose/prompts/` with the stock prompts of the new version: they are edited copies.
