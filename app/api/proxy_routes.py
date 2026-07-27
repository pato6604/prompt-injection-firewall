import logging
from fastapi import APIRouter, Request, HTTPException
from app.api.schemas import ChatCompletionRequest
from app.proxy.request_parser import parse_request
from app.proxy.provider_router import get_provider
from app.proxy.stream_handler import stream_response
from app.detection.pipeline import DetectionPipeline

logger = logging.getLogger(__name__)
router = APIRouter()

# Detection pipeline (lazy singleton)
_detection_pipeline: DetectionPipeline | None = None


def get_detection_pipeline() -> DetectionPipeline:
    global _detection_pipeline
    if _detection_pipeline is None:
        _detection_pipeline = DetectionPipeline()
        _detection_pipeline.load()
    return _detection_pipeline


@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()

    # 1. Parsear y validar
    try:
        chat_request = parse_request(body)
    except Exception as e:
        logger.warning("Request validation failed: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Detection pipeline
    pipeline = get_detection_pipeline()
    message_texts = [m.content for m in chat_request.messages]
    detection = pipeline.run(message_texts)

    if detection.blocked:
        logger.warning(
            "Request BLOCKED: score=%.2f rules=%s",
            detection.risk_score,
            detection.triggered_rules,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "prompt_injection_detected",
                "risk_score": detection.risk_score,
                "triggered_rules": detection.triggered_rules,
                "message": "Request blocked by security policy",
            },
        )

    if detection.flagged:
        logger.info(
            "Request FLAGGED: score=%.2f rules=%s (allowing)",
            detection.risk_score,
            detection.triggered_rules,
        )

    # 3. Obtener proveedor
    try:
        provider = get_provider()
    except ValueError as e:
        logger.error("Provider error: %s", str(e))
        raise HTTPException(status_code=503, detail=str(e))

    # 4. Logging del request
    logger.info(
        "Proxy request: model=%s messages=%d stream=%s risk=%.2f",
        chat_request.model,
        len(chat_request.messages),
        chat_request.stream,
        detection.risk_score,
    )

    # 5. Streaming o no
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
