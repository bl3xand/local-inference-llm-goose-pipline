#!/usr/bin/env python3
"""goose PostToolUse hook (todo, edit, write): keep a PROGRESS entry for the project in global Memory.

Memory is loaded at the start of every session, so the next session sees the last plan and what was actually changed
without the model having to save or search anything. The plan comes from the todo tool; the list of changed files is
recorded here on every edit/write, because models often do not tick their todo items. One entry per project
(category = directory name), replaced on every update, removed when the todo list is emptied or every item is ticked.
Silent: prints nothing (stdout is goose's decision channel). No files are created inside the project.
"""
import json, os, re, sys, time

try:
    p = json.load(sys.stdin)
except Exception:
    sys.exit(0)
tool = str(p.get("tool_name", "")); ti = p.get("tool_input") or {}
wd = os.path.normpath(p.get("working_dir") or os.getcwd())
category = "home" if wd == os.path.expanduser("~") else (re.sub(r"[^A-Za-z0-9._-]+", "-", os.path.basename(wd)).strip("-.") or "general")
state_dir = os.path.expanduser("~/.local/state/goose/todo-mirror"); os.makedirs(state_dir, exist_ok=True)
state_path = os.path.join(state_dir, category + ".json")
try:
    st = json.load(open(state_path))
except Exception:
    st = {"todo": "", "files": []}

if "todo" in tool:
    new = str(ti.get("content") or ti.get("todo") or "").strip()
    boxes = re.findall(r"\[( |x|X)\]", new)
    if not new or (boxes and all(b != " " for b in boxes)):   # list cleared, or every item ticked: task finished
        st = {"todo": "", "files": []}
    else:
        st["todo"] = new
elif tool in ("edit", "write"):
    f = str(ti.get("path") or "")
    if f:
        rel = os.path.relpath(f if os.path.isabs(f) else os.path.join(wd, f), wd)
        if not rel.startswith("..") and rel not in st["files"]:
            st["files"].append(rel)
else:
    sys.exit(0)
json.dump(st, open(state_path, "w"))

mem_dir = os.path.expanduser("~/.config/goose/memory"); os.makedirs(mem_dir, exist_ok=True)
path = os.path.join(mem_dir, category + ".txt")
# Remove only our own two lines (marker + PROGRESS line). goose appends its entries to the end of the file without a
# leading separator, so anything after our lines belongs to the user's memories and must be kept.
lines = open(path).read().split("\n") if os.path.exists(path) else []
kept, i = [], 0
while i < len(lines):
    if lines[i].strip() == "# progress auto":
        i += 2 if i + 1 < len(lines) and lines[i + 1].startswith("PROGRESS of the last session") else 1
        continue
    kept.append(lines[i]); i += 1
body = "\n".join(kept).strip("\n")
if st["todo"] or st["files"]:
    plan = " | ".join(l.strip() for l in st["todo"].splitlines() if l.strip())[:1400] or "(no plan was written)"
    done = ", ".join(st["files"][-40:]) or "none yet"
    entry = "# progress auto\nPROGRESS of the last session in %s (%s). Plan as last written (ticks may be stale): %s || Files actually changed since the plan was made: %s. Before continuing, check these files and the tests." % (wd, time.strftime("%Y-%m-%d %H:%M"), plan, done)
    body = (body + "\n\n" if body else "") + entry
if body:
    open(path, "w").write(body + "\n\n")          # always end with a blank line so appended entries stay separate
elif os.path.exists(path):
    os.remove(path)
