from app.core.config import Settings, settings
from app.schemas.ai import AIRequest
from app.services.ai_service import AIService, AIServiceConfig


class SuccessfulProvider:
    def generate(self, request: AIRequest, *, timeout_seconds: float) -> str:
        assert request.capability == "future_capability"
        assert timeout_seconds == 5.0
        return "Mocked provider response"


class FailingProvider:
    def generate(self, request: AIRequest, *, timeout_seconds: float) -> str:
        raise RuntimeError("provider failure containing a secret")


class TimeoutProvider:
    def generate(self, request: AIRequest, *, timeout_seconds: float) -> str:
        raise TimeoutError("request timed out")


def configured_service_config() -> AIServiceConfig:
    return AIServiceConfig(
        provider="openai_compatible",
        api_key="test-ai-api-key",
        model="test-model",
        api_base_url="https://provider.example/v1",
        timeout_seconds=5.0,
    )


def test_ai_service_configuration_initialization():
    app_settings = Settings(
        SECRET_KEY="test-secret-key-for-ai-settings-only",
        DATABASE_URL="sqlite:///:memory:",
        AI_PROVIDER="openai_compatible",
        AI_API_KEY="configured-key",
        AI_MODEL="configured-model",
        AI_API_BASE_URL="https://provider.example/v1",
        AI_TIMEOUT_SECONDS=7,
    )

    config = AIServiceConfig.from_settings(app_settings)
    service = AIService(config)

    assert config.provider == "openai_compatible"
    assert config.timeout_seconds == 7
    assert service.health().available is True


def test_ai_service_missing_configuration_uses_safe_fallback():
    config = configured_service_config()
    service = AIService(
        AIServiceConfig(
            provider=config.provider,
            api_key="",
            model=config.model,
            api_base_url=config.api_base_url,
            timeout_seconds=config.timeout_seconds,
        )
    )

    response = service.generate(AIRequest(capability="future_capability", prompt="Test prompt"))

    assert service.health().available is False
    assert response.status == "fallback"
    assert response.used_fallback is True
    assert response.error_code == "AI_NOT_CONFIGURED"
    assert response.content is None


def test_ai_service_returns_mocked_provider_response():
    service = AIService(configured_service_config(), provider=SuccessfulProvider())

    response = service.generate(AIRequest(capability="future_capability", prompt="Test prompt"))

    assert response.status == "success"
    assert response.used_fallback is False
    assert response.content == "Mocked provider response"
    assert response.error_code is None


def test_ai_service_provider_failure_uses_safe_fallback():
    service = AIService(configured_service_config(), provider=FailingProvider())

    response = service.generate(AIRequest(capability="future_capability", prompt="Test prompt"))

    assert response.status == "fallback"
    assert response.error_code == "AI_PROVIDER_ERROR"
    assert "secret" not in str(response.model_dump())


def test_ai_service_timeout_uses_safe_fallback():
    service = AIService(configured_service_config(), provider=TimeoutProvider())

    response = service.generate(AIRequest(capability="future_capability", prompt="Test prompt"))

    assert response.status == "fallback"
    assert response.error_code == "AI_TIMEOUT"


def test_ai_health_endpoint_never_exposes_configuration(client, monkeypatch):
    secret = "do-not-return-this-ai-key"
    monkeypatch.setattr(settings, "AI_PROVIDER", "openai_compatible")
    monkeypatch.setattr(settings, "AI_API_KEY", secret)
    monkeypatch.setattr(settings, "AI_MODEL", "private-model-name")
    monkeypatch.setattr(settings, "AI_API_BASE_URL", "https://provider.example/v1")
    monkeypatch.setattr(settings, "AI_TIMEOUT_SECONDS", 5.0)

    response = client.get("/api/v1/health/ai")

    assert response.status_code == 200
    assert response.json() == {"available": True, "status": "available"}
    assert secret not in response.text
    assert "private-model-name" not in response.text
