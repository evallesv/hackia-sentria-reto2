from types import SimpleNamespace

import pytest
from google import genai
from google.genai import types

from app.agent.provider import GeminiProvider, MockProvider, ProviderError
from app.config import Settings
from app.main import load_case


def configuration(**overrides):
    return Settings(
        _env_file=None,
        ai_mode="gemini",
        gemini_api_key="synthetic-test-key",
        gemini_model="test-model",
        **overrides,
    )


def fake_sdk(monkeypatch, response=None, error=None):
    captured = {}

    class Client:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.models = SimpleNamespace(generate_content=self.generate)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def generate(self, **kwargs):
            captured["request"] = kwargs
            if error:
                raise error
            return response

    monkeypatch.setattr(genai, "Client", Client)
    return captured


def sdk_response(name="submit_claim_assessments", finish="STOP", args=None):
    payload = MockProvider().review(load_case("A")).review.model_dump() if args is None else args
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                finish_reason=finish,
                content=types.Content(
                    role="model",
                    parts=[types.Part(function_call=types.FunctionCall(name=name, args=payload))],
                ),
            )
        ],
        model_version="test-resolved-version",
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=100, candidates_token_count=20, thoughts_token_count=5
        ),
    )


def test_gemini_contract_and_budget(monkeypatch):
    captured = fake_sdk(monkeypatch, sdk_response())
    provider = GeminiProvider(configuration(llm_max_calls_per_process=1))
    result = provider.review(load_case("A"))
    assert result.model == "test-resolved-version"
    assert result.output_tokens == 25
    config = captured["request"]["config"]
    assert config.automatic_function_calling.disable is True
    assert config.tool_config.function_calling_config.allowed_function_names == [
        "submit_claim_assessments"
    ]
    assert config.max_output_tokens == 3000
    options = captured["client"]["http_options"]
    assert options.timeout == 30000
    assert options.retry_options.attempts == 1
    assert "$ref" not in str(config.tools[0].function_declarations[0].parameters_json_schema)
    with pytest.raises(ProviderError, match="Límite"):
        provider.review(load_case("A"))


@pytest.mark.parametrize(
    "response",
    [
        sdk_response(name="send_payment"),
        sdk_response(finish="MAX_TOKENS"),
        sdk_response(args={"assessments": []}),
        types.GenerateContentResponse(),
    ],
)
def test_bad_sdk_outputs_fail_closed(monkeypatch, response):
    fake_sdk(monkeypatch, response)
    with pytest.raises(ProviderError):
        GeminiProvider(configuration()).review(load_case("A"))


def test_error_does_not_leak_raw_provider_message(monkeypatch):
    fake_sdk(monkeypatch, error=RuntimeError("secret text and document"))
    with pytest.raises(ProviderError) as error:
        GeminiProvider(configuration()).review(load_case("A"))
    assert "secret" not in str(error.value)


def test_unconfigured_provider_never_calls_sdk(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No SDK call without credentials")

    monkeypatch.setattr(genai, "Client", forbidden)
    with pytest.raises(ProviderError, match="sin configurar"):
        GeminiProvider(Settings(_env_file=None)).review(load_case("A"))
