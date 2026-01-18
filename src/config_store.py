"""Config persistence and redacted API helpers."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from src.config import Config
from src.logger import get_logger

logger = get_logger("config_store")


class ConfigStore:
    """Persist config in /data/config.json."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or Path("/data/config.json")

    def load(self) -> Dict[str, Any]:
        """Load saved config JSON."""
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Failed to read config.json, using defaults")
            return {}

    def save(self, payload: Dict[str, Any]) -> None:
        """Persist config JSON to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def merge_config(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge updates into base dict."""
    result = deepcopy(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_config(result[key], value)
        else:
            result[key] = value
    return result


def load_effective_config(env: Mapping[str, str], store: Optional[ConfigStore] = None) -> Config:
    """Load config from saved store plus env overrides."""
    store = store or ConfigStore()
    saved = store.load()
    return Config.from_sources(env, saved=saved)


def redacted_effective_config(env: Mapping[str, str], store: Optional[ConfigStore] = None) -> Dict[str, Any]:
    """Return redacted effective config for API output."""
    config = load_effective_config(env, store=store)
    return config.to_dict(redact=True)
