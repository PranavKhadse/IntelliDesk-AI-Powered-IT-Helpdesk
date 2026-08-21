"""Provider-neutral AI foundation for future IntelliDesk capabilities."""

from dataclasses import dataclass
from typing import Protocol
import json

import httpx

from app.core.config import Settings, settings
from app.schemas.ai import AIHealthResponse, AIRequest, AIResponse


class AIProvider(Protocol):
    """Minimal contract future AI providers must implement."""

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
        return cls(
            provider=app_settings.AI_PROVIDER.strip().lower(),
            api_key=app_settings.AI_API_KEY.strip(),
            model=app_settings.AI_MODEL.strip(),
            api_base_url=app_settings.AI_API_BASE_URL.strip(),
            timeout_seconds=app_settings.AI_TIMEOUT_SECONDS,
        )


class OpenAICompatibleProvider:
    """Small adapter for providers offering the OpenAI chat-completions contract."""

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
            headers={"Authorization": f"Bearer {self._config.api_key}"},
            json=payload,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Provider returned an empty completion.")
        return content.strip()


class AIService:
    """Stable, failure-safe AI entry point used by future application services."""

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
        except (TimeoutError, httpx.TimeoutException):
            return self._fallback("AI_TIMEOUT")
        except Exception:
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
