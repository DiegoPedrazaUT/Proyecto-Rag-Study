import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flashcards import Flashcard, FlashcardView


class ViewRepository:
    """Acceso a datos para el log de vistas de flashcards."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_view(
        self, *, flashcard_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """Registra una vista de forma idempotente.

        Usa INSERT ... ON CONFLICT DO NOTHING sobre la restricción única
        (flashcard_id, user_id): si la vista ya existe, no hace nada y no
        falla. Así llamar al endpoint varias veces es seguro.
        """
        stmt = (
            pg_insert(FlashcardView)
            .values(flashcard_id=flashcard_id, user_id=user_id)
            .on_conflict_do_nothing(constraint="uq_flashcard_view")
        )
        await self.db.execute(stmt)

    async def list_views_for_card(
        self, flashcard_id: uuid.UUID
    ) -> list[FlashcardView]:
        """Lista las vistas de una tarjeta (quién la vio), más recientes primero."""
        stmt = (
            select(FlashcardView)
            .where(FlashcardView.flashcard_id == flashcard_id)
            .order_by(FlashcardView.viewed_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_unseen_cards(
        self, *, deck_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[Flashcard]:
        """Tarjetas de un mazo que el usuario aún NO ha visto.

        Subconsulta: ids de tarjetas ya vistas por el usuario; se excluyen.
        """
        seen_subq = (
            select(FlashcardView.flashcard_id)
            .where(FlashcardView.user_id == user_id)
            .scalar_subquery()
        )
        stmt = (
            select(Flashcard)
            .where(
                Flashcard.deck_id == deck_id,
                Flashcard.id.not_in(seen_subq),
            )
            .order_by(Flashcard.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())