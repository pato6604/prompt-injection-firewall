from typing import AsyncIterator, Protocol
from app.api.schemas import ChatCompletionRequest, ChatCompletionResponse

class LLMProvider(Protocol):
    async def chat(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        ...

    async def stream(
        self, request: ChatCompletionRequest
    ) -> AsyncIterator[str]:
        ...