from pydantic import BaseModel
from typing import Literal, Optional

# --- Chat Completion Request ---

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool", "developer"]
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "gpt-4o-mini"
    messages: list[ChatMessage]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = False
    # otros parámetros opcionales se pasan como extra

# --- Chat Completion Response (no-stream) ---

class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class Choice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[Choice]
    usage: Usage

# --- Streaming chunks (SSE) ---

class DeltaChoice(BaseModel):
    index: int = 0
    delta: dict  # {role?, content?}
    finish_reason: Optional[str] = None

class ChatCompletionChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: list[DeltaChoice]
