from __future__ import annotations

from typing import Dict
try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

_CACHE: Dict[str, Dict[str, str]] | None = None


def load_descriptions(path: str = "data/descriptions.yaml") -> Dict[str, Dict[str, str]]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    data: Dict[str, Dict[str, str]] = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            if yaml is None:
                # Minimal fallback: return empty if PyYAML is unavailable
                raw = {}
            else:
                raw = yaml.safe_load(f) or {}
        if isinstance(raw, dict):
            # Normalize keys to lowercase strings
            for k, v in raw.items():
                if isinstance(v, dict):
                    data[str(k).lower()] = {str(sub_k).lower(): str(sub_v) for sub_k, sub_v in v.items()}
    except Exception:
        data = {}
    _CACHE = data
    return _CACHE


def get_description(name: str, lang: str = "en") -> str:
    data = load_descriptions()
    entry = data.get(str(name).lower())
    if not isinstance(entry, dict):
        return ""
    return entry.get(str(lang).lower(), "").strip()
