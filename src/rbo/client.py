from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ApiResult:
    response: dict[str, Any]
    started_at: float
    ended_at: float


class OpenAIChatClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str = "EMPTY",
        timeout: float = 900.0,
        post_json: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._post_json = post_json

    def create(self, body: dict[str, Any]) -> ApiResult:
        started = time.monotonic()
        if self._post_json is not None:
            response = self._post_json(body)
            return ApiResult(response=response, started_at=started, ended_at=time.monotonic())

        data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self.base_url,
            data=data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:  # noqa: S310 local/user endpoint
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI-compatible API HTTP {exc.code}: {detail[:1000]}") from exc
        return ApiResult(response=payload, started_at=started, ended_at=time.monotonic())
