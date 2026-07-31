"""initial database schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("key_prefix", sa.String(length=32), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)

    op.create_table(
        "policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("block_threshold", sa.Float(), nullable=False),
        sa.Column("flag_threshold", sa.Float(), nullable=False),
        sa.Column("rules_overrides", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "security_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("api_key_id", sa.Integer(), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("messages_count", sa.Integer(), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("triggered_rules", sa.JSON(), nullable=False),
        sa.Column("normalized_text_preview", sa.String(length=500), nullable=False),
        sa.Column("blocked", sa.Boolean(), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"]),
    )
    op.create_index("ix_security_events_request_id", "security_events", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_security_events_request_id", table_name="security_events")
    op.drop_table("security_events")
    op.drop_table("policies")
    op.drop_index("ix_api_keys_key_hash", table_name="api_keys")
    op.drop_table("api_keys")
