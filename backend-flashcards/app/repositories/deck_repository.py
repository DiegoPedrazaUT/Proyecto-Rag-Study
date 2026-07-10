import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.external import OrganizationMember
from app.models.flashcards import Flashcard, FlashcardDeck


class DeckRepository:
    """Acceso a datos para mazos. Sin lógica de negocio ni commits."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add(self, deck: FlashcardDeck) -> FlashcardDeck:
        self.db.add(deck)
        await self.db.flush()
        return deck
    
    async def delete(self, deck: FlashcardDeck) -> None:
        await self.db.delete(deck)
        await self.db.flush()

    async def is_member(
        self, *, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> bool:
        """True si el usuario pertenece al salón indicado."""
        stmt = select(OrganizationMember.user_id).where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == organization_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_deck(self, deck_id: uuid.UUID) -> FlashcardDeck | None:
        """Trae un mazo sin sus tarjetas (para chequeos de autorización)."""
        result = await self.db.execute(
            select(FlashcardDeck).where(FlashcardDeck.id == deck_id)
        )
        return result.scalar_one_or_none()

    async def get_deck_with_cards(
        self, deck_id: uuid.UUID
    ) -> FlashcardDeck | None:
        """Trae un mazo con sus flashcards precargadas (selectinload).

        selectinload evita el problema N+1 y el lazy-load (que no funciona
        en sesiones async). Las tarjetas se ordenan luego por created_at.
        """
        stmt = (
            select(FlashcardDeck)
            .where(FlashcardDeck.id == deck_id)
            .options(selectinload(FlashcardDeck.cards))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self, user_id: uuid.UUID
    ) -> list[tuple[FlashcardDeck, int]]:
        """Mazos del usuario, cada uno con su conteo de tarjetas.

        Un solo query con LEFT JOIN + GROUP BY para evitar el problema N+1.
        Devuelve tuplas (deck, card_count), de más reciente a más antiguo.
        """
        stmt = (
            select(FlashcardDeck, func.count(Flashcard.id))
            .outerjoin(Flashcard, Flashcard.deck_id == FlashcardDeck.id)
            .where(FlashcardDeck.user_id == user_id)
            .group_by(FlashcardDeck.id)
            .order_by(FlashcardDeck.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]
    
    async def list_by_organization(
        self, organization_id: uuid.UUID
    ) -> list[tuple[FlashcardDeck, int]]:
        """Todos los mazos de un salón, con su conteo de tarjetas.

        No filtra por creador: devuelve los mazos de cualquier miembro.
        """
        stmt = (
            select(
                FlashcardDeck,
                func.count(Flashcard.id).label("card_count"),
            )
            .outerjoin(Flashcard, Flashcard.deck_id == FlashcardDeck.id)
            .where(FlashcardDeck.organization_id == organization_id)
            .group_by(FlashcardDeck.id)
            .order_by(FlashcardDeck.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]