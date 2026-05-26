from __future__ import annotations

import json
from pathlib import Path

from rbo.summary import summarize_runs


def test_summarize_runs_reads_bundle_summaries(tmp_path: Path) -> None:
    run = tmp_path / "run-a"
    (run / "reports").mkdir(parents=True)
    (run / "reports" / "summary.json").write_text(json.dumps({"run_id": "run-a", "accuracy": 0.5, "attempts": 2}) + "\n")
    (tmp_path / "index.jsonl").write_text(json.dumps({"run_id": "run-a", "bundle_path": str(run)}) + "\n")

    summary = summarize_runs(tmp_path)

    assert summary == [{"run_id": "run-a", "accuracy": 0.5, "attempts": 2}]
