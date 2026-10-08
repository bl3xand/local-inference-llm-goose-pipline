#!/usr/bin/env python3
"""goose extension "vision": lets any local model look at image files.

goose only forwards images to models listed as vision-capable in its built-in catalog, which local models are not in.
This MCP server (stdio, no dependencies beyond the Python standard library, ImageMagick for conversion) gives the agent
a `view_image` tool instead: it converts the image from any format, sends it to the local llama-server and returns text.
"""
import base64, json, os, subprocess, sys, tempfile, urllib.request

SERVER = os.environ.get("VISION_SERVER", "http://127.0.0.1:8080")
FALLBACK_MODEL = os.environ.get("VISION_MODEL", "ornith-1.5-35b")   # used when the loaded model cannot see
MAX_SIDE = os.environ.get("VISION_MAX_SIDE", "1600")
DEFAULT_QUESTION = ("Transcribe all text in this image exactly, then describe everything else that matters "
                    "(what application or object it shows, layout, state) in a few sentences.")
TOOL = {
    "name": "view_image",
    "description": ("Look at an image FILE ON DISK (screenshot, photo, diagram; PNG, JPEG, WebP, HEIC, GIF, BMP...) and answer a "
                    "question about it. Use it ONLY when you have a real path to a file: the user named it, or you found it "
                    "with a command. Do NOT use it for a picture attached to the chat message: that picture is already "
                    "visible to you, it is not a file, and names like input_file_0.png do not exist. "
                    "Always pass the user's actual question so the answer is about what they asked."),
    "inputSchema": {"type": "object", "required": ["path"], "properties": {
        "path": {"type": "string", "description": "Path to the image file (absolute, or relative to the working directory)."},
        "question": {"type": "string", "description": "What to find out about the image, in the user's language."}}},
}


def http(path, payload=None, timeout=240):
    req = urllib.request.Request(SERVER + path, json.dumps(payload).encode() if payload else None, {"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def pick_model():
    """Prefer the model that is already in VRAM if it has a vision projector; otherwise the fallback vision model."""
    try:
        for m in http("/v1/models", timeout=10).get("data", []):
            loaded = (m.get("status") or {}).get("value") == "loaded"
            args = " ".join((m.get("status") or {}).get("args") or [])
            if loaded and "--mmproj" in args:
                return m["id"]
    except Exception:
        pass
    return FALLBACK_MODEL


def view_image(path, question):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.expanduser(path)
        if not os.path.isfile(path):
            return ("There is no file " + path + ". If you mean the picture attached to the chat message: it is not a file, "
                    "you already see it directly - just look at it and answer. Do not call view_image again for it. "
                    "This tool is only for image files that really exist on disk.")
        jpg = os.path.join(tmp, "i.jpg")
        conv = subprocess.run(["magick", path + "[0]", "-auto-orient", "-resize", f"{MAX_SIDE}x{MAX_SIDE}>", "-quality", "90", jpg],
                              capture_output=True, text=True)
        if conv.returncode != 0 or not os.path.isfile(jpg):
            return "Could not read this file as an image: " + (conv.stderr.strip().splitlines() or ["unknown format"])[-1][:200]
        url = "data:image/jpeg;base64," + base64.b64encode(open(jpg, "rb").read()).decode()
    body = {"model": pick_model(), "reasoning_effort": "none", "max_tokens": 1500, "messages": [{"role": "user", "content": [
        {"type": "text", "text": question or DEFAULT_QUESTION}, {"type": "image_url", "image_url": {"url": url}}]}]}
    try:
        return http("/v1/chat/completions", body)["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Vision request failed ({type(e).__name__}): {e}"


def reply(msg_id, result=None, error=None):
    out = {"jsonrpc": "2.0", "id": msg_id}
    out.update({"error": error} if error else {"result": result})
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n"); sys.stdout.flush()


for line in sys.stdin:
    try:
        msg = json.loads(line)
    except ValueError:
        continue
    method, mid, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
    if mid is None:
        continue                                    # notifications need no answer
    if method == "initialize":
        reply(mid, {"protocolVersion": params.get("protocolVersion", "2025-06-18"), "capabilities": {"tools": {}},
                    "serverInfo": {"name": "vision", "version": "1.0.0"}})
    elif method == "tools/list":
        reply(mid, {"tools": [TOOL]})
    elif method == "tools/call":
        a = params.get("arguments") or {}
        if params.get("name") != "view_image" or not a.get("path"):
            reply(mid, {"content": [{"type": "text", "text": "view_image needs a 'path' argument."}], "isError": True})
        else:
            reply(mid, {"content": [{"type": "text", "text": view_image(a["path"], a.get("question"))}]})
    elif method == "ping":
        reply(mid, {})
    else:
        reply(mid, error={"code": -32601, "message": "method not found: " + str(method)})
