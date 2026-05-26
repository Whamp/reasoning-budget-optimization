from __future__ import annotations

import json
from pathlib import Path

from rbo.baselines import default_baseline_specs
from rbo.bundle import write_run_bundle
from rbo.runner import run_bundle


class WhitespaceTokenizer:
    def encode(self, text: str, add_special_tokens: bool = False) -> list[str]:
        return text.split()
from rbo.scoring import parse_aime_answer, score_aime_answer


def test_parse_and_score_aime_boxed_integer() -> None:
    assert parse_aime_answer("Therefore the answer is \\boxed{588}.") == "588"
    assert parse_aime_answer("Final answer: 588") == "588"
    assert score_aime_answer("\\boxed{588}", "588").correct is True
    assert score_aime_answer("\\boxed{587}", "588").correct is False


def test_run_bundle_writes_attempts_and_summary_with_fake_client(tmp_path: Path) -> None:
    spec = default_baseline_specs(timestamp="20260526-1700", seeds=[20260413])[1]  # guard bundle has 2 items
    bundle = write_run_bundle(tmp_path, spec)

    def fake_post(body: dict) -> dict:
        assert body["model"] == "Jackrong/Qwopus3.6-27B-v2"
        assert body["thinking_token_budget"] == 8192
        target = "588" if "heptagon" in body["messages"][0]["content"] else "123"
        return {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "reasoning": "partial work My reasoning budget is exhausted, but I have enough information to answer directly now.",
                        "content": f"\\boxed{{{target}}}",
                    },
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

    summary = run_bundle(bundle, post_json=fake_post, start_serving=False)

    assert summary["attempts"] == 2
    assert summary["correct"] == 1
    assert summary["budget_hits"] == 2
    attempts = [json.loads(line) for line in (bundle / "attempts.jsonl").read_text().splitlines()]
    assert {a["item_id"] for a in attempts} == {"1", "19"}
    assert all(a["reasoning_end_str_seen"] for a in attempts)
    assert json.loads((bundle / "reports" / "summary.json").read_text()) == summary


def test_plain_close_budget_hit_can_use_tokenizer_estimate(tmp_path: Path) -> None:
    spec = next(s for s in default_baseline_specs(timestamp="20260526-1700", seeds=[20260413]) if s.string_label == "plain-close" and s.role == "opt")
    bundle = write_run_bundle(tmp_path, spec)

    def fake_post(body: dict) -> dict:
        return {
            "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "reasoning": "x " * 8192, "content": "\\boxed{0}"}}],
            "usage": {},
        }

    summary = run_bundle(bundle, post_json=fake_post, start_serving=False, tokenizer=WhitespaceTokenizer())

    attempts = [json.loads(line) for line in (bundle / "attempts.jsonl").read_text().splitlines()]
    assert summary["budget_hits"] == 3
    assert all(a["hit_detection_method"] == "tokenizer_estimate" for a in attempts)
