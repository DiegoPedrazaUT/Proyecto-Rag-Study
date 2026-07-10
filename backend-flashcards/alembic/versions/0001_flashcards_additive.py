"""Aditiva flashcards: organization_id en decks + tabla flashcard_views

Revision ID: 0001_flashcards_additive
Revises:
Create Date: 2026-06-20

Asume que las tablas base (users, organizations, flashcard_decks, flashcards)
ya existen, creadas por los otros módulos. Esta migración solo AÑADE.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_flashcards_additive"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Nueva columna organization_id en flashcard_decks.
    #    Se agrega como nullable para no romper filas existentes; luego
    #    se backfillea y se vuelve NOT NULL.
    op.add_column(
        "flashcard_decks",
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_flashcard_decks_organization_id",
        source_table="flashcard_decks",
        referent_table="organizations",
        local_cols=["organization_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_flashcard_decks_organization_id",
        "flashcard_decks",
        ["organization_id"],
    )

    # 2) Tabla flashcard_views (log de vistas por usuario).
    op.create_table(
        "flashcard_views",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "flashcard_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("flashcards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "viewed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc'::text, now())"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_flashcard_views_flashcard_user",
        "flashcard_views",
        ["flashcard_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_flashcard_views_flashcard_user", table_name="flashcard_views")
    op.drop_table("flashcard_views")
    op.drop_index(
        "ix_flashcard_decks_organization_id", table_name="flashcard_decks"
    )
    op.drop_constraint(
        "fk_flashcard_decks_organization_id",
        "flashcard_decks",
        type_="foreignkey",
    )
    op.drop_column("flashcard_decks", "organization_id")
