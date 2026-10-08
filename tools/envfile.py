"""Settings of this machine: example.env gives the defaults, .env (not in git) overrides them."""
import os

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def _read(path):
    out = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            out[k.strip()] = v
    return out


def load(home=None):
    """All settings as strings. `home` replaces the real home folder (used for a trial install into another folder)."""
    env = _read(os.path.join(REPO, "example.env"))
    env.update(_read(os.path.join(REPO, ".env")))
    real_home = os.path.expanduser("~")
    for k, v in env.items():
        if v.startswith("~"):
            v = real_home + v[1:]
        env[k] = v.replace("$HOME", real_home)
    env["HOME"] = home or real_home
    env["REPO_DIR"] = REPO
    if not env.get("MODELS_DIR"):
        env["MODELS_DIR"] = os.path.join(REPO, "models")
    return env


def per_model(text):
    """'name=1230 other=2048' -> {'name': '1230', 'other': '2048'}"""
    return dict(x.split("=", 1) for x in (text or "").split() if "=" in x)
