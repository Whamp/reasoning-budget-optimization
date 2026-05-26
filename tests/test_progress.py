from __future__ import annotations

from rbo.progress import ProgressReporter


def test_progress_reporter_tracks_per_item_hits_and_correct_counts(capsys) -> None:
    reporter = ProgressReporter(run_id="run-a", total=3, every=1)

    reporter.record({"item_id": "12", "seed": 1, "correct": True, "budget_hit": True, "hit_detection_method": "tokenizer_estimate", "latency_ms": 1000})
    reporter.record({"item_id": "12", "seed": 2, "correct": False, "budget_hit": False, "hit_detection_method": "not_detected", "latency_ms": 2000})
    reporter.record({"item_id": "24", "seed": 1, "correct": True, "budget_hit": True, "hit_detection_method": "reasoning_end_str_seen", "latency_ms": 3000})

    output = capsys.readouterr().out
    assert "completed=1/3" in output
    assert "item_hits=12:1/1" in output
    assert "item_hits=12:1/2,24:1/1" in output
    assert "hit_correct=2" in output
