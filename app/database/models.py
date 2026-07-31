from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarativa para los modelos persistentes."""


class ApiKey(Base):
    """API key interna almacenada solo como hash irreversible."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(32), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list["SecurityEvent"]] = relationship(back_populates="api_key")


class SecurityEvent(Base):
    """Evento auditable para cada request evaluado por el firewall."""

    __tablename__ = "security_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    request_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    api_key_id: Mapped[int | None] = mapped_column(ForeignKey("api_keys.id"), nullable=True)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    messages_count: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    triggered_rules: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    normalized_text_preview: Mapped[str] = mapped_column(String(500), nullable=False)
    blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    api_key: Mapped[ApiKey | None] = relationship(back_populates="events")


class Policy(Base):
    """Politica configurable por tenant."""

    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, default="default")
    block_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    flag_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)
    rules_overrides: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
