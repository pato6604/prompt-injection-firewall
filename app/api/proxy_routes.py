import hashlib
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.decision_cache import get_decision_cache
from app.config import settings
from app.database.session import get_db
from app.proxy.request_parser import parse_request
from app.proxy.provider_router import get_provider
from app.proxy.stream_handler import stream_response
from app.detection.normalizer import normalize
from app.detection.pipeline import DetectionPipeline, DetectionResult
from app.detection.scorer import DetectionDecision
from app.observability.audit import audit_security_event
from app.security.authentication import require_api_key
from app.security.rate_limit import get_rate_limiter

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
async def chat_completions(request: Request, db: AsyncSession = Depends(get_db)):
    api_key = await require_api_key(request, db)
    rate_key = str(api_key.id) if api_key is not None else "anonymous"
    allowed = await get_rate_limiter().check(rate_key)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(settings.rate_limit_window_seconds)},
        )

    body = await request.json()

    # 1. Parsear y validar
    try:
        chat_request = parse_request(body)
    except Exception as e:
        logger.warning("Request validation failed: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Detection pipeline con cache por texto normalizado
    pipeline = get_detection_pipeline()
    message_texts = [m.content for m in chat_request.messages]
    normalized = normalize("\n".join(message_texts))
    cache_key = hashlib.sha256(normalized.normalized.encode("utf-8")).hexdigest()
    cached = await get_decision_cache().get(cache_key)
    if cached is not None:
        detection = DetectionResult(
            risk_score=float(cached["risk_score"]),
            decision=DetectionDecision(cached["decision"]),
            triggered_rules=list(cached.get("triggered_rules", [])),
            normalized_text=normalized.normalized[:500],
            has_invisible_chars=normalized.has_invisible_chars,
            homoglyphs_found=len(normalized.homoglyphs_found),
            encoding_detected=normalized.encoding_detected,
            max_severity=cached.get("max_severity", "none"),
        )
    else:
        detection = pipeline.run(message_texts)
        await get_decision_cache().set(
            cache_key,
            {
                "risk_score": detection.risk_score,
                "decision": detection.decision.value,
                "triggered_rules": detection.triggered_rules,
                "max_severity": detection.max_severity,
            },
            settings.decision_cache_ttl_seconds,
        )

    await audit_security_event(
        db,
        request_id=request.state.request_id,
        api_key_id=api_key.id if api_key is not None else None,
        model=chat_request.model,
        messages_count=len(chat_request.messages),
        risk_score=detection.risk_score,
        decision=detection.decision.value,
        triggered_rules=detection.triggered_rules,
        normalized_preview=detection.normalized_text,
        blocked=detection.blocked,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

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
                "request_id": request.state.request_id,
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
