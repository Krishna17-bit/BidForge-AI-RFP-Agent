from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .config import settings
from .utils import truncate


class LLMError(RuntimeError):
    pass


@dataclass
class LLMResult:
    text: str
    engine_used: str


class LLMGateway:
    """Gemini-first LLM gateway with Groq fallback.

    The provider is intentionally configured by environment only, so the UI can stay
    clean and client-facing.
    """

    def __init__(self):
        self.temperature = settings.temperature

    def generate(self, prompt: str, *, system: Optional[str] = None, json_mode: bool = False) -> LLMResult:
        prompt = truncate(prompt, settings.max_chars_per_prompt)
        errors: list[str] = []

        if settings.gemini_api_key:
            try:
                return LLMResult(self._gemini(prompt, system=system, json_mode=json_mode), "primary")
            except Exception as exc:  # fallback should keep app usable
                errors.append(f"Gemini failed: {exc}")

        if settings.groq_api_key:
            try:
                return LLMResult(self._groq(prompt, system=system, json_mode=json_mode), "fallback")
            except Exception as exc:
                errors.append(f"Groq failed: {exc}")

        raise LLMError("No working LLM API key found. Add GEMINI_API_KEY and/or GROQ_API_KEY in .env. " + " | ".join(errors))

    def _gemini(self, prompt: str, *, system: Optional[str], json_mode: bool) -> str:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.gemini_api_key)
        config_kwargs = {
            "temperature": self.temperature,
        }
        if system:
            config_kwargs["system_instruction"] = system
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(**config_kwargs),
        )
        return getattr(response, "text", "") or ""

    def _groq(self, prompt: str, *, system: Optional[str], json_mode: bool) -> str:
        from groq import Groq

        client = Groq(api_key=settings.groq_api_key)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        kwargs = {
            "model": settings.groq_model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            completion = client.chat.completions.create(**kwargs)
        except Exception:
            kwargs.pop("response_format", None)
            completion = client.chat.completions.create(**kwargs)
        return completion.choices[0].message.content or ""
