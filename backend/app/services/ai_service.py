"""Provider-neutral AI foundation for IntelliDesk capabilities."""

from dataclasses import dataclass
from typing import Protocol
import re
import json
import logging

import httpx

from app.core.config import Settings, settings
from app.schemas.ai import AIHealthResponse, AIRequest, AIResponse

logger = logging.getLogger("app.ai_service")


class AIProvider(Protocol):
    """Minimal contract AI providers must implement."""

    def generate(self, request: AIRequest, *, timeout_seconds: float) -> str:
        """Return generated text or raise a provider-specific error."""


@dataclass(frozen=True)
class AIServiceConfig:
    provider: str
    api_key: str
    model: str
    api_base_url: str
    timeout_seconds: float

    @classmethod
    def from_settings(cls, app_settings: Settings) -> "AIServiceConfig":
        raw_provider = getattr(app_settings, "effective_ai_provider", app_settings.AI_PROVIDER).strip().lower()
        api_key = getattr(app_settings, "effective_ai_api_key", app_settings.AI_API_KEY).strip()
        model = app_settings.AI_MODEL.strip()
        api_base_url = app_settings.AI_API_BASE_URL.strip()

        # Handle provider auto-configuration and alias mappings
        provider = raw_provider
        if provider in ("gemini", "google"):
            provider = "openai_compatible"
            if not api_base_url:
                api_base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
            if not model:
                model = "gemini-flash-lite-latest"
        elif provider in ("openai",):
            provider = "openai_compatible"
            if not api_base_url:
                api_base_url = "https://api.openai.com/v1"
            if not model:
                model = "gpt-4o-mini"
        elif provider in ("ollama",):
            provider = "openai_compatible"
            if not api_base_url:
                api_base_url = "http://localhost:11434/v1"
            if not model:
                model = "llama3"

        return cls(
            provider=provider,
            api_key=api_key,
            model=model,
            api_base_url=api_base_url,
            timeout_seconds=app_settings.AI_TIMEOUT_SECONDS,
        )


class OpenAICompatibleProvider:
    """Adapter for providers offering the OpenAI chat-completions contract."""

    def __init__(self, config: AIServiceConfig):
        self._config = config

    def generate(self, request: AIRequest, *, timeout_seconds: float) -> str:
        payload = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": f"You are assisting IntelliDesk with {request.capability}."},
                {"role": "user", "content": request.prompt},
            ],
        }
        if request.context:
            payload["messages"].append({"role": "user", "content": json.dumps(request.context)})
        if request.max_output_tokens is not None:
            payload["max_tokens"] = request.max_output_tokens
        if request.response_format == "json_object":
            payload["response_format"] = {"type": "json_object"}

        response = httpx.post(
            f"{self._config.api_base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._config.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        res_json = response.json()
        choices = res_json.get("choices", [])
        if not choices or not isinstance(choices, list):
            raise ValueError("Provider returned an invalid response structure.")
        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Provider returned an empty completion.")

        raw_text = content.strip()
        # Clean markdown code fences if wrapped by LLM (e.g. ```json ... ```)
        if "```" in raw_text:
            fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
            if fence_match:
                raw_text = fence_match.group(1).strip()
            elif raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()
        elif request.response_format == "json_object":
            start_idx = raw_text.find("{")
            end_idx = raw_text.rfind("}")
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                raw_text = raw_text[start_idx : end_idx + 1].strip()
        return raw_text


class AIService:
    """Stable, failure-safe AI entry point used by application services."""

    def __init__(self, config: AIServiceConfig, provider: AIProvider | None = None):
        self._config = config
        self._provider = provider or self._initialize_provider()

    def _initialize_provider(self) -> AIProvider | None:
        if not self._is_configured():
            return None
        if self._config.provider == "openai_compatible":
            return OpenAICompatibleProvider(self._config)
        return None

    def _is_configured(self) -> bool:
        return bool(
            self._config.provider == "openai_compatible"
            and self._config.api_key
            and self._config.model
            and self._config.api_base_url
            and self._config.timeout_seconds > 0
        )

    def health(self) -> AIHealthResponse:
        available = self._provider is not None
        return AIHealthResponse(available=available, status="available" if available else "unavailable")

    def generate(self, request: AIRequest) -> AIResponse:
        if self._provider is None:
            return self._fallback("AI_NOT_CONFIGURED")

        try:
            content = self._provider.generate(request, timeout_seconds=self._config.timeout_seconds)
            return AIResponse(content=content, status="success", used_fallback=False)
        except (TimeoutError, httpx.TimeoutException) as e:
            logger.warning("AI provider request timed out (%s)", type(e).__name__)
            return self._fallback("AI_TIMEOUT")
        except httpx.HTTPStatusError as e:
            logger.error("AI provider returned HTTP status %s", e.response.status_code)
            return self._fallback("AI_PROVIDER_ERROR")
        except Exception as e:
            logger.error("AI provider unexpected error (%s)", type(e).__name__)
            return self._fallback("AI_PROVIDER_ERROR")

    @staticmethod
    def _fallback(error_code: str) -> AIResponse:
        return AIResponse(
            content=None,
            status="fallback",
            used_fallback=True,
            error_code=error_code,
        )


def get_ai_service() -> AIService:
    """Construct a service from backend-only environment configuration."""

    return AIService(AIServiceConfig.from_settings(settings))
