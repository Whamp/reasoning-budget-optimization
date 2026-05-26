from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_items(item_ids: tuple[str, ...]) -> list[dict[str, Any]]:
    all_items: dict[str, dict[str, Any]] = {}
    for path in (PROJECT_ROOT / "manifests").glob("aime25-*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data["items"]:
            all_items[str(item["item_id"])] = item
    missing = [item_id for item_id in item_ids if item_id not in all_items]
    if missing:
        raise KeyError(f"missing manifest items: {', '.join(missing)}")
    return [all_items[item_id] for item_id in item_ids]
