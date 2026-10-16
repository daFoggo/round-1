import os
import random
import re
import time
from typing import Optional

import requests

from app.config import settings


class LLMClient:
    """Client OpenRouter (Qwen3.7 Flash) với xử lý rate limit và thống kê token/chi phí."""

    def __init__(
        self,
        openrouter_key: Optional[str] = None,
        model: Optional[str] = None,
        openrouter_base_url: Optional[str] = None,
    ):
        self.openrouter_key = openrouter_key or settings.openrouter_api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.openrouter_model = model or settings.openrouter_model
        self.openrouter_base_url = (openrouter_base_url or settings.openrouter_base_url).rstrip("/")
        # Thống kê (token gồm input + reasoning là tiêu chí xếp hạng thứ 3)
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
                      "reasoning_tokens": 0, "cost": 0.0, "calls": 0}

    @property
    def active_model(self) -> str:
        return self.openrouter_model

    def generate_response(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.0) -> str:
        if not self.openrouter_key:
            raise ValueError("OpenRouter API key is not configured (--openrouter-key / OPENROUTER_API_KEY).")
        url = f"{self.openrouter_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ai-tai-nang-2026.local",
            "X-Title": "AI Tai Nang 2026 Round 1",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.openrouter_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": settings.max_output_tokens,
        }
        # Reasoning được tính vào token và làm chậm mạnh: 'none' = tắt hoàn toàn
        effort = settings.openrouter_reasoning_effort.lower()
        payload["reasoning"] = {"enabled": False} if effort == "none" else {"effort": effort}

        last_error: Optional[Exception] = None
        for attempt in range(settings.llm_max_attempts):
            try:
                res = requests.post(url, headers=headers, json=payload, timeout=settings.llm_timeout)
            except (requests.ConnectionError, requests.Timeout) as e:
                last_error = e
                self._sleep_backoff(attempt, None)
                continue

            # 429: giới hạn từ OpenRouter/provider; 402 in_flight_budget_exhausted và 5xx: tạm thời
            if res.status_code in (429, 500, 502, 503, 504) or (
                res.status_code == 402 and self._is_transient_402(res)
            ):
                last_error = requests.HTTPError(f"{res.status_code} from OpenRouter: {res.text[:200]}", response=res)
                self._sleep_backoff(attempt, res.headers.get("Retry-After"))
                continue

            res.raise_for_status()  # 4xx còn lại (401, 403, 402 weight_exceeds_budget...) không thử lại
            data = res.json()
            self._record_usage(data.get("usage") or {})
            choices = data.get("choices", [])
            if not choices:
                return ""
            msg = choices[0].get("message", {})
            # Lỗi giữa chừng (vd. 429 trong stream) trả về finish_reason 'error'
            if choices[0].get("finish_reason") == "error" and not msg.get("content"):
                last_error = RuntimeError(f"OpenRouter finish_reason=error: {data.get('error')}")
                self._sleep_backoff(attempt, None)
                continue
            return msg.get("content") or ""
        raise last_error if last_error else RuntimeError("OpenRouter call failed")

    @staticmethod
    def _is_transient_402(res) -> bool:
        try:
            meta = (res.json().get("error") or {}).get("metadata") or {}
            return meta.get("reason") == "in_flight_budget_exhausted" or meta.get("limit_source") == "in_flight_budget"
        except Exception:
            return False

    @staticmethod
    def _sleep_backoff(attempt: int, retry_after) -> None:
        """Ưu tiên Retry-After của server; nếu không có thì backoff mũ có jitter. Không sleep khi request bình thường."""
        try:
            delay = float(retry_after) if retry_after is not None else None
        except ValueError:
            delay = None
        if delay is None:
            delay = min(2 ** attempt, 20) + random.uniform(0, 1)
        time.sleep(min(delay, settings.llm_max_backoff))

    def _record_usage(self, usage: dict) -> None:
        for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
            self.usage[k] += int(usage.get(k) or 0)
        details = usage.get("completion_tokens_details") or {}
        self.usage["reasoning_tokens"] += int(details.get("reasoning_tokens") or 0)
        self.usage["cost"] += float(usage.get("cost") or 0.0)
        self.usage["calls"] += 1

    @staticmethod
    def extract_python_code(text: str) -> str:
        pattern = r"```(?:python)?\s*([\s\S]*?)```"
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            return matches[0].strip()
        return text.strip()
