from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

PROD_LONG_TRANSITION = "My reasoning budget is exhausted, but I have enough information to answer directly now."
CLOSE_THINK = "</think>"


def validate_transition_text(text: str) -> list[str]:
    errors: list[str] = []
    if "<think>" in text or "</think>" in text:
        errors.append("transition_text must not contain <think> or </think>; the harness appends </think>")
    if len(text) > 200:
        errors.append("transition_text must be <= 200 characters")
    return errors


def render_reasoning_end_string(transition_text: str) -> str:
    errors = validate_transition_text(transition_text)
    if errors:
        raise ValueError("; ".join(errors))
    return transition_text + CLOSE_THINK


@dataclass(frozen=True)
class ReasoningConfig:
    reasoning_start_str: str
    reasoning_end_str: str

    def to_json_obj(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ServingConfig:
    label: str
    model_id: str
    served_model_name: str
    container_name: str = "rbo-vllm"
    host_port: int = 30001
    image: str = "vllm/vllm-openai:nightly"
    tensor_parallel_size: int = 4
    max_num_seqs: int = 8
    max_model_len: str = "131072"
    max_num_batched_tokens: int = 8192
    gpu_memory_utilization: float = 0.9
    tool_call_parser: str = "qwen3_coder"
    reasoning_parser: str | None = "qwen3"
    reasoning_config: ReasoningConfig | None = None


@dataclass(frozen=True)
class RequestConfig:
    mode: str
    max_tokens: int = 81920
    temperature: float = 0.95
    top_p: float = 0.95
    top_k: int = 20
    min_p: float = 0.0
    repetition_penalty: float = 1.0
    thinking_token_budget: int | None = None
    chat_template_kwargs: dict[str, Any] | None = None

    def to_request_fields(self) -> dict[str, Any]:
        fields: dict[str, Any] = {
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "min_p": self.min_p,
            "repetition_penalty": self.repetition_penalty,
        }
        if self.thinking_token_budget is not None:
            fields["thinking_token_budget"] = self.thinking_token_budget
        if self.chat_template_kwargs:
            fields["chat_template_kwargs"] = self.chat_template_kwargs
        return fields


@dataclass(frozen=True)
class RunSpec:
    run_id: str
    model_slug: str
    string_label: str
    role: Literal["opt", "guard"]
    mode: str
    item_ids: tuple[str, ...]
    seeds: tuple[int, ...]
    serving: ServingConfig
    request: RequestConfig
    transition_text: str | None

    def to_manifest(self) -> dict[str, Any]:
        return {
            "storage_version": 1,
            "run_id": self.run_id,
            "model_slug": self.model_slug,
            "string_label": self.string_label,
            "role": self.role,
            "mode": self.mode,
            "items": list(self.item_ids),
            "seeds": list(self.seeds),
            "transition_text": self.transition_text,
            "reasoning_end_str": self.serving.reasoning_config.reasoning_end_str if self.serving.reasoning_config else None,
            "serving": _dataclass_to_dict(self.serving),
            "request": self.request.to_request_fields(),
        }


def _dataclass_to_dict(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {k: _dataclass_to_dict(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _dataclass_to_dict(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_dataclass_to_dict(v) for v in value]
    return value
