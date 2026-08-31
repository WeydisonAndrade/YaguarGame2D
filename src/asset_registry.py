"""Manifesto de assets e checagem de arquivos faltantes (só em debug)."""
from __future__ import annotations

import json
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
MANIFEST_PATH = ASSETS_DIR / "manifest.json"

# Caminhos relativos a assets/. Críticos = o gameplay quebra sem fallback visual.
CRITICAL_FALLBACKS = (
    "parallax/forest1.png",
    "parallax/forest2.png",
    "parallax/mapinguari_arena.png",
    "player/idle.png",
    "player/jump.png",
)


def load_manifest() -> list[dict]:
    if not MANIFEST_PATH.is_file():
        return []
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items = data.get("assets", data) if isinstance(data, dict) else data
    return items if isinstance(items, list) else []


def missing_assets(include_optional: bool = True) -> list[dict]:
    missing = []
    for item in load_manifest():
        rel = item.get("path", "")
        if not rel:
            continue
        if not include_optional and item.get("optional"):
            continue
        path = ASSETS_DIR / rel
        if not path.is_file():
            missing.append(item)
    return missing


def warn_missing_assets(debug: bool) -> list[str]:
    """Em desenvolvimento, imprime MISSING ASSET. No build final, silêncio."""
    if not debug:
        return []
    lines = []
    for item in missing_assets(include_optional=True):
        rel = item.get("path", "")
        line = f"MISSING ASSET: assets/{rel}"
        print(line)
        lines.append(line)
    for rel in CRITICAL_FALLBACKS:
        if not (ASSETS_DIR / rel).is_file():
            line = f"MISSING ASSET: assets/{rel}"
            print(line)
            lines.append(line)
    return lines
