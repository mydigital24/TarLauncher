"""Persistent registry of installed tar.gz applications."""

import json
import os
import uuid
from datetime import datetime


def data_dir():
    base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    d = os.path.join(base, "gearleverfortar")
    os.makedirs(d, exist_ok=True)
    return d


def registry_path():
    return os.path.join(data_dir(), "apps.json")


def load_registry():
    p = registry_path()
    if not os.path.exists(p):
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def save_registry(entries):
    p = registry_path()
    with open(p, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def new_id():
    return str(uuid.uuid4())


def now_iso():
    return datetime.now().isoformat(timespec="seconds")
