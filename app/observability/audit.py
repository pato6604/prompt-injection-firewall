from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories import log_security_event


async def audit_security_event(
    db: AsyncSession,
    *,
    request_id: str,
    api_key_id: int | None,
    model: str,
    messages_count: int,
    risk_score: float,
    decision: str,
    triggered_rules: list[Any],
    normalized_preview: str,
    blocked: bool,
    ip_address: str | None,
    user_agent: str | None,
):
    """Registra un evento de seguridad para auditoria y SIEM."""
    return await log_security_event(
        db,
        request_id=request_id,
        api_key_id=api_key_id,
        model=model,
        messages_count=messages_count,
        risk_score=risk_score,
        decision=decision,
        triggered_rules=triggered_rules,
        normalized_text_preview=normalized_preview[:500],
        blocked=blocked,
        ip_address=ip_address,
        user_agent=user_agent,
    )
