from app.api.schemas import ChatCompletionRequest

from typing import Any

def is_empty_or_whitespace(value: Any) -> bool:
    return isinstance(value, str) and (not value.strip())

def parse_request(body: dict) -> ChatCompletionRequest:
    if not body.get("messages"):
        raise ValueError("Field 'messages' cannot be empty.")
    if is_empty_or_whitespace(body.get("model")):
        raise ValueError("Field 'model' cannot be empty or whitespace.")
    for message in body.get("messages"):
        if is_empty_or_whitespace(message.get("content")):
            raise ValueError("Message content cannot be empty or whitespace.")
    return ChatCompletionRequest(**body)
