from __future__ import annotations

import json
import time
from typing import Any, Optional

from openai import OpenAI

from backend.config import settings


class LLMAdapter:
    """纯 LLM 适配器，只负责 messages -> 文本输出。"""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
    ) -> None:
        self._api_key = api_key or settings.llm_api_key
        self._base_url = base_url or settings.llm_base_url
        self._default_model = default_model or settings.llm_model_name or settings.llm_model
        self._max_retries = max(1, max_retries)
        self._retry_delay_seconds = max(0.0, retry_delay_seconds)
        self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)

    def generate_text(self, messages: list[dict[str, Any]], model: Optional[str] = None) -> str:
        selected_model = model or self._default_model
        last_error: Optional[Exception] = None

        for attempt in range(1, self._max_retries + 1):
            try:
                completion = self._client.chat.completions.create(
                    model=selected_model,
                    messages=messages,
                )
                return completion.choices[0].message.content or ""
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt >= self._max_retries:
                    break
                time.sleep(self._retry_delay_seconds * attempt)

        assert last_error is not None
        raise last_error

    def generate_tool_call(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_choice: dict[str, Any] | str,
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        selected_model = model or self._default_model
        last_error: Optional[Exception] = None

        for attempt in range(1, self._max_retries + 1):
            try:
                completion = self._client.chat.completions.create(
                    model=selected_model,
                    messages=messages,
                    tools=tools,
                    tool_choice=tool_choice,
                )
                message = completion.choices[0].message
                tool_calls = getattr(message, "tool_calls", None) or []
                if not tool_calls:
                    raise ValueError("LLM 未返回任何 tool call。")

                selected_tool_call = tool_calls[0]
                raw_arguments = selected_tool_call.function.arguments or "{}"
                parsed_arguments = json.loads(raw_arguments)
                return {
                    "tool_name": selected_tool_call.function.name,
                    "arguments": parsed_arguments,
                }
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt >= self._max_retries:
                    break
                time.sleep(self._retry_delay_seconds * attempt)

        assert last_error is not None
        raise last_error
