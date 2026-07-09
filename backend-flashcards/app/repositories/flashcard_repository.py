import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flashcards import Flashcard, FlashcardDeck


class FlashcardRepository:
    """Acceso a datos para flashcards. Sin lógica de negocio ni commits."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_deck(self, deck_id: uuid.UUID) -> FlashcardDeck | None:
        result = await self.db.execute(
            select(FlashcardDeck).where(FlashcardDeck.id == deck_id)
        )
        return result.scalar_one_or_none()

    async def get_card(self, card_id: uuid.UUID) -> Flashcard | None:
        result = await self.db.execute(
            select(Flashcard).where(Flashcard.id == card_id)
        )
        return result.scalar_one_or_none()

    async def add_cards(self, cards: list[Flashcard]) -> list[Flashcard]:
        self.db.add_all(cards)
        await self.db.flush()
        return cards

    async def delete_card(self, card: Flashcard) -> None:
        await self.db.delete(card)
        await self.db.flush()