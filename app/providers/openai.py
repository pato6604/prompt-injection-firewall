import json
import logging
from typing import AsyncIterator
import httpx
from app.api.schemas import (
    ChatCompletionRequest, ChatCompletionResponse,
    Choice, ChatMessage, Usage,
)

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """Adaptador para la API de OpenAI (compatible con Chat Completions)."""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    async def chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """Non-streaming chat completion.

        Envía el request a OpenAI y devuelve la respuesta parsed en los schemas del proyecto.
        """
        payload = request.model_dump(exclude_none=True)
        payload.pop("stream", None)

        try:
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
        except httpx.TimeoutException:
            logger.error("OpenAI request timed out")
            raise RuntimeError("OpenAI API request timed out")
        except httpx.HTTPStatusError as e:
            error_body = ""
            try:
                error_body = e.response.text
            except Exception:
                pass
            logger.error("OpenAI returned HTTP %s: %s", e.response.status_code, error_body)
            raise RuntimeError(f"OpenAI API error ({e.response.status_code}): {error_body}")
        except httpx.RequestError as e:
            logger.error("OpenAI request failed: %s", str(e))
            raise RuntimeError(f"OpenAI connection error: {str(e)}")

        data = response.json()

        return ChatCompletionResponse(
            id=data["id"],
            created=data["created"],
            model=data["model"],
            choices=[
                Choice(
                    index=c["index"],
                    message=ChatMessage(
                        role=c["message"]["role"],
                        content=c["message"]["content"],
                    ),
                    finish_reason=c.get("finish_reason", "stop"),
                )
                for c in data["choices"]
            ],
            usage=Usage(
                prompt_tokens=data["usage"]["prompt_tokens"],
                completion_tokens=data["usage"]["completion_tokens"],
                total_tokens=data["usage"]["total_tokens"],
            ),
        )

    async def stream(self, request: ChatCompletionRequest) -> AsyncIterator[str]:
        """Streaming chat completion. Yields SSE-formatted strings (data: ...)."""
        payload = request.model_dump(exclude_none=True)
        payload["stream"] = True

        try:
            async with self.client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        yield line
                    elif line.strip() == "data: [DONE]":
                        yield line
        except httpx.TimeoutException:
            logger.error("OpenAI streaming request timed out")
            raise RuntimeError("OpenAI streaming request timed out")
        except httpx.HTTPStatusError as e:
            error_body = ""
            try:
                error_body = e.response.text
            except Exception:
                pass
            logger.error("OpenAI streaming returned HTTP %s: %s", e.response.status_code, error_body)
            raise RuntimeError(f"OpenAI streaming error ({e.response.status_code}): {error_body}")
        except httpx.RequestError as e:
            logger.error("OpenAI streaming failed: %s", str(e))
            raise RuntimeError(f"OpenAI streaming connection error: {str(e)}")

    async def close(self):
        await self.client.aclose()
