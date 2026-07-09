import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.models.flashcards import FlashcardDeck
from app.repositories.deck_repository import DeckRepository
from app.schemas.deck import DeckCreate, DeckDetail, DeckWithCount
from app.schemas.flashcard import FlashcardRead


class DeckService:
    """Lógica de negocio para mazos. Aquí viven autorización y commits."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DeckRepository(db)

    async def create_empty_deck(
        self, *, payload: DeckCreate, current_user: CurrentUser
    ) -> FlashcardDeck:
        is_member = await self.repo.is_member(
            user_id=current_user.id,
            organization_id=payload.organization_id,
        )
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No perteneces a este salón.",
            )

        deck = FlashcardDeck(
            user_id=current_user.id,
            organization_id=payload.organization_id,
            document_id=payload.document_id,
            title=payload.title,
        )
        await self.repo.add(deck)
        await self.db.commit()
        await self.db.refresh(deck)
        return deck

    async def list_user_decks(
        self, *, current_user: CurrentUser
    ) -> list[DeckWithCount]:
        """Lista los mazos creados por el usuario, con conteo de tarjetas."""
        rows = await self.repo.list_by_user(current_user.id)
        return [
            DeckWithCount(
                id=deck.id,
                user_id=deck.user_id,
                organization_id=deck.organization_id,
                document_id=deck.document_id,
                title=deck.title,
                created_at=deck.created_at,
                card_count=count,
            )
            for deck, count in rows
        ]

    async def get_deck_detail(
        self, *, deck_id: uuid.UUID, current_user: CurrentUser
    ) -> DeckDetail:
        """Devuelve un mazo con sus tarjetas.

        Visible para cualquier miembro del salón del mazo (no solo el dueño).
        """
        deck = await self.repo.get_deck_with_cards(deck_id)
        if deck is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El mazo no existe.",
            )

        is_member = await self.repo.is_member(
            user_id=current_user.id,
            organization_id=deck.organization_id,
        )
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No perteneces al salón de este mazo.",
            )

        cards = sorted(deck.cards, key=lambda c: c.created_at)
        return DeckDetail(
            id=deck.id,
            user_id=deck.user_id,
            organization_id=deck.organization_id,
            document_id=deck.document_id,
            title=deck.title,
            created_at=deck.created_at,
            cards=[FlashcardRead.model_validate(c) for c in cards],
        )
    
    async def delete_deck(
        self, *, deck_id: uuid.UUID, current_user: CurrentUser
    ) -> None:
        """Elimina un mazo y, en cascada, todas sus flashcards.

        El borrado en cascada lo hace Postgres vía la FK con ondelete=CASCADE.
        Solo el dueño del mazo puede eliminarlo.
        """
        deck = await self.repo.get_deck(deck_id)
        if deck is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El mazo no existe.",
            )
        if deck.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No eres el dueño de este mazo.",
            )

        await self.repo.delete(deck)
        await self.db.commit()
    
