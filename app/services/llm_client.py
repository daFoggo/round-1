import os
import re
import time
import requests
from typing import Optional
from app.config import settings

class LLMClient:
    def __init__(
        self,
        provider: Optional[str] = None,
        gemini_key: Optional[str] = None,
        openrouter_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.provider = (provider or settings.llm_provider).lower()
        self.gemini_key = gemini_key or settings.gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        self.openrouter_key = openrouter_key or settings.openrouter_api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.openrouter_model = model or settings.openrouter_model
        self.gemini_model = model or settings.gemini_model

    def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if self.provider == "gemini":
            return self._call_gemini(prompt, system_prompt)
        elif self.provider == "openrouter":
            return self._call_openrouter(prompt, system_prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _call_gemini(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.gemini_key:
            raise ValueError("GEMINI_API_KEY is not configured.")
        
        models_to_try = [self.gemini_model, "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": system_prompt}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will strictly follow these instructions."}]})
        
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 2048,
            }
        }
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": self.gemini_key
        }

        last_error = None
        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            for attempt in range(3):
                try:
                    res = requests.post(url, headers=headers, json=payload, timeout=30)
                    if res.status_code == 200:
                        data = res.json()
                        candidates = data.get("candidates", [])
                        if not candidates:
                            return ""
                        parts = candidates[0].get("content", {}).get("parts", [])
                        return "".join(p.get("text", "") for p in parts)
                    elif res.status_code in [503, 429]:
                        time.sleep(2 * (attempt + 1))
                        continue
                    else:
                        res.raise_for_status()
                except Exception as e:
                    last_error = e
                    time.sleep(1)

        if last_error:
            raise last_error
        return ""

    def _call_openrouter(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.openrouter_key:
            raise ValueError("OPENROUTER_API_KEY is not configured.")
        url = "https://openrouter.ai/api/v1/chat/completions"
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
            "temperature": 0.0,
            "max_tokens": 2048,
        }
        res = requests.post(url, headers=headers, json=payload, timeout=40)
        res.raise_for_status()
        data = res.json()
        choices = data.get("choices", [])
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "")

    @staticmethod
    def extract_python_code(text: str) -> str:
        pattern = r"```(?:python)?\s*([\s\S]*?)```"
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            return matches[0].strip()
        return text.strip()
