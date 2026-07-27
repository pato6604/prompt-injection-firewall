import logging
from app.config import settings
from app.providers.openai import OpenAIProvider

logger = logging.getLogger(__name__)

_provider = None


def get_provider():
    global _provider
    if _provider is None:
        api_key = settings.openai_api_key
        if not api_key or not api_key.strip():
            logger.error("OpenAI API key is not configured. Set OPENAI_API_KEY in .env")
            raise ValueError("OpenAI API key cannot be empty.")

        _provider = OpenAIProvider(
            api_key=api_key,
            base_url=settings.openai_base_url,
        )
    return _provider


async def close_provider():
    global _provider
    if _provider:
        await _provider.close()
        _provider = None
