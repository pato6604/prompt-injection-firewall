import logging
from fastapi import APIRouter, Request, HTTPException
from app.api.schemas import ChatCompletionRequest
from app.proxy.request_parser import parse_request
from app.proxy.provider_router import get_provider
from app.proxy.stream_handler import stream_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()

    # 1. Parsear y validar
    try:
        chat_request = parse_request(body)
    except Exception as e:
        logger.warning("Request validation failed: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Obtener proveedor
    provider = get_provider()

    # 3. Logging del request
    logger.info(
        "Proxy request: model=%s messages=%d stream=%s",
        chat_request.model,
        len(chat_request.messages),
        chat_request.stream,
    )

    # 4. Streaming o no
    if chat_request.stream:
        logger.debug("Starting streaming response for %s", chat_request.model)
        stream_iter = provider.stream(chat_request)
        return await stream_response(stream_iter)
    else:
        response = await provider.chat(chat_request)
        logger.info(
            "Proxy response: model=%s tokens=%d+%d",
            response.model,
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
        )
        return response.model_dump()
