from __future__ import annotations

import json
from pathlib import Path

from rbo.baseline_runner import iter_bundle_paths, plan_baseline_suite, run_baseline_suite
from rbo.baselines import default_baseline_specs
from rbo.bundle import write_run_bundle


def test_iter_bundle_paths_reads_ledger_and_skips_completed_by_default(tmp_path: Path) -> None:
    specs = default_baseline_specs(timestamp="20260526-1901", seeds=[20260413])[:2]
    first = write_run_bundle(tmp_path, specs[0])
    second = write_run_bundle(tmp_path, specs[1])
    (first / "reports").mkdir(exist_ok=True)
    (first / "reports" / "summary.json").write_text(json.dumps({"run_id": specs[0].run_id}) + "\n")

    assert list(iter_bundle_paths(tmp_path)) == [second]
    assert list(iter_bundle_paths(tmp_path, rerun=True)) == [first, second]


def test_plan_baseline_suite_reports_pending_without_running(tmp_path: Path) -> None:
    specs = default_baseline_specs(timestamp="20260526-1901", seeds=[20260413])[:2]
    for spec in specs:
        write_run_bundle(tmp_path, spec)

    planned = plan_baseline_suite(tmp_path)

    assert planned == [spec.run_id for spec in specs]


def test_run_baseline_suite_runs_not_run_bundles_with_one_loaded_tokenizer(tmp_path: Path) -> None:
    specs = default_baseline_specs(timestamp="20260526-1901", seeds=[20260413])[:2]
    for spec in specs:
        write_run_bundle(tmp_path, spec)
    calls: list[tuple[str, int, bool, object]] = []
    tokenizer = object()

    def runner(bundle: Path, **kwargs):
        calls.append((bundle.name, kwargs["concurrency"], kwargs["start_serving"], kwargs["tokenizer"]))
        summary = {"run_id": bundle.name, "attempts": 1, "correct": 1, "accuracy": 1.0, "budget_hits": 1, "hit_accuracy": 1.0}
        reports = bundle / "reports"
        reports.mkdir(exist_ok=True)
        (reports / "summary.json").write_text(json.dumps(summary) + "\n")
        return summary

    summaries = run_baseline_suite(tmp_path, tokenizer=tokenizer, concurrency=8, start_serving=True, runner=runner)

    assert len(summaries) == 2
    assert [call[1:] for call in calls] == [(8, True, tokenizer), (8, True, tokenizer)]
