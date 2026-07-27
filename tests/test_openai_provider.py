from app.providers.openai import OpenAIProvider


def test_openai_provider_structure():
    provider = OpenAIProvider(api_key="test_key")
    assert provider.api_key == "test_key"
    assert provider.base_url == "https://api.openai.com/v1"
