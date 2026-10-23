"""User preferences in config.json (PsyDocs' pattern: never blocks the app)."""
import json
import os
import sys
from pathlib import Path

APP_NAME = "PsySet"


def _config_dir() -> str:
    if sys.platform == "darwin":
        return os.path.expanduser(os.path.join("~/Library/Application Support", APP_NAME))
    if os.name == "nt":
        return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)
    return os.path.expanduser(os.path.join("~/.config", APP_NAME))


def config_path() -> Path:
    return Path(_config_dir()) / "config.json"


def load_config() -> dict:
    try:
        cfg = json.loads(config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return cfg if isinstance(cfg, dict) else {}


def save_config(cfg: dict) -> None:
    try:
        p = config_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass  # preferences must never block the app
