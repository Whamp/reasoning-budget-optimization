from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .client import OpenAIChatClient
from .manifest import load_items
from .scoring import score_aime_answer


def run_bundle(
    bundle_dir: Path,
    *,
    endpoint: str = "http://localhost:30001/v1/chat/completions",
    api_key: str = "EMPTY",
    post_json: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    start_serving: bool = False,
) -> dict[str, Any]:
    if start_serving:
        from .server_control import start_bundle_serving, wait_ready

        start_bundle_serving(bundle_dir)
        wait_ready("http://localhost:30001/v1/models", bundle_dir=bundle_dir)

    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    request_config = json.loads((bundle_dir / "rendered" / "request_config.json").read_text(encoding="utf-8"))
    items = load_items(tuple(manifest["items"]))
    client = OpenAIChatClient(base_url=endpoint, api_key=api_key, post_json=post_json)

    attempts_path = bundle_dir / "attempts.jsonl"
    raw_path = bundle_dir / "raw" / "responses.jsonl"
    attempts_path.write_text("", encoding="utf-8")
    raw_path.write_text("", encoding="utf-8")

    rows: list[dict[str, Any]] = []
    for seed in manifest["seeds"]:
        for item in items:
            body = {
                "model": manifest["serving"]["served_model_name"],
                "messages": [{"role": "user", "content": item["prompt"]}],
                "seed": seed,
                **request_config,
            }
            api = client.create(body)
            response = api.response
            raw_row = {"run_id": manifest["run_id"], "item_id": item["item_id"], "seed": seed, "response": response}
            _append_jsonl(raw_path, raw_row)
            row = _attempt_from_response(manifest, item, seed, response, api.started_at, api.ended_at)
            _append_jsonl(attempts_path, row)
            rows.append(row)

    summary = summarize_attempts(manifest, rows)
    reports = bundle_dir / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (reports / "summary.md").write_text(_summary_markdown(summary), encoding="utf-8")
    return summary


def summarize_attempts(manifest: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    attempts = len(rows)
    correct = sum(1 for row in rows if row.get("correct"))
    budget_hits = sum(1 for row in rows if row.get("budget_hit"))
    hit_correct = sum(1 for row in rows if row.get("budget_hit") and row.get("correct"))
    latencies = [row["latency_ms"] for row in rows if row.get("latency_ms") is not None]
    return {
        "run_id": manifest["run_id"],
        "role": manifest["role"],
        "mode": manifest["mode"],
        "string_label": manifest["string_label"],
        "attempts": attempts,
        "correct": correct,
        "wrong": attempts - correct,
        "accuracy": correct / attempts if attempts else 0.0,
        "budget_hits": budget_hits,
        "hit_correct": hit_correct,
        "hit_wrong": budget_hits - hit_correct,
        "hit_accuracy": hit_correct / budget_hits if budget_hits else None,
        "avg_latency_ms": sum(latencies) / len(latencies) if latencies else None,
    }


def _attempt_from_response(
    manifest: dict[str, Any],
    item: dict[str, Any],
    seed: int,
    response: dict[str, Any],
    started_at: float,
    ended_at: float,
) -> dict[str, Any]:
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content") or ""
    reasoning = message.get("reasoning") or message.get("reasoning_content") or ""
    score = score_aime_answer(content, item["target"])
    reasoning_end = manifest.get("reasoning_end_str")
    transition = manifest.get("transition_text") or ""
    seen = bool(reasoning_end and (reasoning_end in reasoning or reasoning_end in content))
    if not seen and transition:
        seen = transition in reasoning or transition in content
    mode = str(manifest.get("mode"))
    budget_hit = bool(seen and mode.startswith("budgeted:"))
    usage = response.get("usage") or {}
    return {
        "run_id": manifest["run_id"],
        "item_id": item["item_id"],
        "seed": seed,
        "status": "completed",
        "correct": score.correct,
        "parsed_answer": score.parsed_answer,
        "target": score.target,
        "budget_hit": budget_hit,
        "reasoning_end_str_seen": seen,
        "latency_ms": int((ended_at - started_at) * 1000),
        "finish_reason": choice.get("finish_reason"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "raw_output": content,
        "raw_reasoning": reasoning,
    }


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True, default=str) + "\n")


def _summary_markdown(summary: dict[str, Any]) -> str:
    return f"""# {summary['run_id']}

- attempts: {summary['attempts']}
- correct: {summary['correct']}
- accuracy: {summary['accuracy']:.3f}
- budget hits: {summary['budget_hits']}
- hit correct: {summary['hit_correct']}
- hit accuracy: {summary['hit_accuracy'] if summary['hit_accuracy'] is not None else 'n/a'}
"""
