"""
Version loaded from config.yaml (single source of truth).
Used by: FastAPI, /api/health, /api/system/info, MQTT device info, tests.
"""
from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"


def _load_version() -> str:
    try:
        if _CONFIG_PATH.exists():
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return str(data.get("version", "0.0.0")).strip()
    except Exception:
        pass
    return "0.0.0"


__version__ = _load_version()
