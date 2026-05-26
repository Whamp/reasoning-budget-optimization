from __future__ import annotations

from .domain import (
    PROD_LONG_TRANSITION,
    ReasoningConfig,
    RequestConfig,
    RunSpec,
    ServingConfig,
    render_reasoning_end_string,
)

DEFAULT_MODEL_ID = "Jackrong/Qwopus3.6-27B-v2-FP8"
DEFAULT_SERVED_MODEL_NAME = "Jackrong/Qwopus3.6-27B-v2"
DEFAULT_MODEL_SLUG = "qwopus-v2-fp8"
DEFAULT_SEEDS = tuple(range(20260413, 20260418))
OPT_ITEMS = ("12", "24", "27")
GUARD_ITEMS = ("1", "19")


def default_baseline_specs(*, timestamp: str, seeds: list[int] | tuple[int, ...] = DEFAULT_SEEDS) -> list[RunSpec]:
    seed_tuple = tuple(seeds)
    specs: list[RunSpec] = []
    for string_label, transition in (("prod-long", PROD_LONG_TRANSITION), ("plain-close", "")):
        serving = _cutoff_serving(label=string_label, transition_text=transition)
        request = RequestConfig(mode="budgeted:8192", thinking_token_budget=8192)
        specs.extend(_role_specs(timestamp, string_label, "b8192", seed_tuple, serving, request, transition))

    disabled_serving = _cutoff_serving(label="server-prod-long", transition_text=PROD_LONG_TRANSITION)
    disabled_request = RequestConfig(mode="disabled", chat_template_kwargs={"enable_thinking": False})
    specs.extend(_role_specs(timestamp, "server-prod-long", "disabled", seed_tuple, disabled_serving, disabled_request, PROD_LONG_TRANSITION))

    unlimited_serving = ServingConfig(
        label="no-reasoning-config",
        model_id=DEFAULT_MODEL_ID,
        served_model_name=DEFAULT_SERVED_MODEL_NAME,
        reasoning_parser=None,
        reasoning_config=None,
    )
    unlimited_request = RequestConfig(mode="unlimited")
    specs.extend(_role_specs(timestamp, "no-reasoning-config", "unlimited", seed_tuple, unlimited_serving, unlimited_request, None))
    return specs


def _cutoff_serving(*, label: str, transition_text: str) -> ServingConfig:
    return ServingConfig(
        label=label,
        model_id=DEFAULT_MODEL_ID,
        served_model_name=DEFAULT_SERVED_MODEL_NAME,
        reasoning_parser="qwen3",
        reasoning_config=ReasoningConfig(
            reasoning_start_str="<think>",
            reasoning_end_str=render_reasoning_end_string(transition_text),
        ),
    )


def _role_specs(
    timestamp: str,
    string_label: str,
    mode_label: str,
    seeds: tuple[int, ...],
    serving: ServingConfig,
    request: RequestConfig,
    transition_text: str | None,
) -> list[RunSpec]:
    seed_label = _seed_label(seeds)
    return [
        RunSpec(
            run_id=f"{timestamp}_{DEFAULT_MODEL_SLUG}_{string_label}_{mode_label}_opt-12-24-27_{seed_label}",
            model_slug=DEFAULT_MODEL_SLUG,
            string_label=string_label,
            role="opt",
            mode=request.mode,
            item_ids=OPT_ITEMS,
            seeds=seeds,
            serving=serving,
            request=request,
            transition_text=transition_text,
        ),
        RunSpec(
            run_id=f"{timestamp}_{DEFAULT_MODEL_SLUG}_{string_label}_{mode_label}_guard-1-19_{seed_label}",
            model_slug=DEFAULT_MODEL_SLUG,
            string_label=string_label,
            role="guard",
            mode=request.mode,
            item_ids=GUARD_ITEMS,
            seeds=seeds,
            serving=serving,
            request=request,
            transition_text=transition_text,
        ),
    ]


def _seed_label(seeds: tuple[int, ...]) -> str:
    if len(seeds) == 1:
        return f"s{seeds[0]}"
    return f"s{seeds[0]}-{seeds[-1]}"
