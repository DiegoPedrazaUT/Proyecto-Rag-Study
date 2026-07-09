import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.models.flashcards import Flashcard, FlashcardDeck, FlashcardView
from app.repositories.deck_repository import DeckRepository
from app.repositories.flashcard_repository import FlashcardRepository
from app.repositories.view_repository import ViewRepository


class ViewService:
    """Lógica de negocio para el registro y consulta de vistas."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.views = ViewRepository(db)
        self.decks = DeckRepository(db)
        self.cards = FlashcardRepository(db)

    async def _get_deck_or_404(self, deck_id: uuid.UUID) -> FlashcardDeck:
        deck = await self.decks.get_deck(deck_id)
        if deck is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El mazo no existe.",
            )
        return deck

    async def _require_member(
        self, *, deck: FlashcardDeck, current_user: CurrentUser
    ) -> None:
        is_member = await self.decks.is_member(
            user_id=current_user.id,
            organization_id=deck.organization_id,
        )
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No perteneces al salón de este mazo.",
            )

    async def _get_card_in_deck_or_404(
        self, *, deck_id: uuid.UUID, card_id: uuid.UUID
    ) -> Flashcard:
        card = await self.cards.get_card(card_id)
        if card is None or card.deck_id != deck_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La flashcard no existe en este mazo.",
            )
        return card

    async def register_view(
        self,
        *,
        deck_id: uuid.UUID,
        card_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> None:
        """Registra que el usuario vio una tarjeta. Cualquier miembro puede.

        Idempotente: registrar dos veces no duplica ni falla.
        """
        deck = await self._get_deck_or_404(deck_id)
        await self._require_member(deck=deck, current_user=current_user)
        await self._get_card_in_deck_or_404(deck_id=deck_id, card_id=card_id)

        await self.views.register_view(
            flashcard_id=card_id, user_id=current_user.id
        )
        await self.db.commit()

    async def list_card_views(
        self,
        *,
        deck_id: uuid.UUID,
        card_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> list[FlashcardView]:
        """Lista quién vio una tarjeta. Solo el dueño del mazo (analítica)."""
        deck = await self._get_deck_or_404(deck_id)
        if deck.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el dueño del mazo puede ver esta información.",
            )
        await self._get_card_in_deck_or_404(deck_id=deck_id, card_id=card_id)
        return await self.views.list_views_for_card(card_id)

    async def list_unseen(
        self, *, deck_id: uuid.UUID, current_user: CurrentUser
    ) -> list[Flashcard]:
        """Tarjetas del mazo que el usuario aún no ha visto. Cualquier miembro."""
        deck = await self._get_deck_or_404(deck_id)
        await self._require_member(deck=deck, current_user=current_user)
        return await self.views.list_unseen_cards(
            deck_id=deck_id, user_id=current_user.id
        )