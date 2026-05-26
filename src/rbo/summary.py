from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def summarize_runs(runs_root: Path) -> list[dict[str, Any]]:
    ledger = runs_root / "index.jsonl"
    if not ledger.exists():
        return []
    summaries: list[dict[str, Any]] = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        bundle = Path(record["bundle_path"])
        summary_path = bundle / "reports" / "summary.json"
        if summary_path.exists():
            summaries.append(json.loads(summary_path.read_text(encoding="utf-8")))
        else:
            summaries.append({
                "run_id": record["run_id"],
                "status": "not-run",
                "role": record.get("role"),
                "mode": record.get("mode"),
                "string_label": record.get("string_label"),
                "items": record.get("items"),
                "seeds": record.get("seeds"),
            })
    return summaries


def format_summary_table(rows: list[dict[str, Any]]) -> str:
    headers = ["run_id", "status", "attempts", "correct", "accuracy", "budget_hits", "hit_accuracy"]
    out = ["\t".join(headers)]
    for row in rows:
        out.append("\t".join(_cell(row.get(h)) for h in headers))
    return "\n".join(out) + "\n"


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)
