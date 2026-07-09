import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.models.flashcards import Flashcard
from app.repositories.flashcard_repository import FlashcardRepository
from app.schemas.flashcard import FlashcardBulkCreate, FlashcardUpdate
from app.services.llm_service import LLMService
from app.schemas.llm import LLMEditProposal


class FlashcardService:
    """Lógica de negocio para flashcards."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = FlashcardRepository(db)

    async def add_cards_to_deck(
        self,
        *,
        deck_id: uuid.UUID,
        payload: FlashcardBulkCreate,
        current_user: CurrentUser,
    ) -> list[Flashcard]:
        deck = await self.repo.get_deck(deck_id)
        if deck is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El mazo no existe.",
            )
        # Agregar tarjetas es una edición: solo el dueño del mazo puede.
        if deck.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No eres el dueño de este mazo.",
            )

        cards = [
            Flashcard(
                deck_id=deck_id,
                front_text=c.front_text,
                back_text=c.back_text,
            )
            for c in payload.cards
        ]
        await self.repo.add_cards(cards)
        await self.db.commit()
        for card in cards:
            await self.db.refresh(card)
        return cards

    async def update_card(
        self,
        *,
        deck_id: uuid.UUID,
        card_id: uuid.UUID,
        payload: FlashcardUpdate,
        current_user: CurrentUser,
    ) -> Flashcard:
        deck = await self.repo.get_deck(deck_id)
        if deck is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El mazo no existe.",
            )
        # Editar es solo del dueño del mazo.
        if deck.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No eres el dueño de este mazo.",
            )

        card = await self.repo.get_card(card_id)
        # La tarjeta debe existir Y pertenecer al mazo de la URL.
        if card is None or card.deck_id != deck_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La flashcard no existe en este mazo.",
            )

        # Solo se actualizan los campos enviados (parcial).
        data = payload.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(card, field, value)

        await self.db.commit()
        await self.db.refresh(card)
        return card
    
    async def delete_card(
        self,
        *,
        deck_id: uuid.UUID,
        card_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> None:
        deck = await self.repo.get_deck(deck_id)
        if deck is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El mazo no existe.",
            )
        # Eliminar es solo del dueño del mazo.
        if deck.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No eres el dueño de este mazo.",
            )

        card = await self.repo.get_card(card_id)
        # La tarjeta debe existir Y pertenecer al mazo de la URL.
        if card is None or card.deck_id != deck_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La flashcard no existe en este mazo.",
            )

        await self.repo.delete_card(card)
        await self.db.commit()

    async def propose_llm_edit(
        self,
        *,
        deck_id: uuid.UUID,
        card_id: uuid.UUID,
        instruction: str,
        current_user: CurrentUser,
    ) -> LLMEditProposal:
        """Genera una propuesta de edición de una flashcard usando la LLM.

        No guarda nada: devuelve la propuesta para que el usuario la revise
        y, si le gusta, la aplique con el PATCH existente. Solo el dueño puede.
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

        card = await self.repo.get_card(card_id)
        if card is None or card.deck_id != deck_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La flashcard no existe en este mazo.",
            )

        llm = LLMService()
        return await llm.edit_flashcard(
            front_text=card.front_text,
            back_text=card.back_text,
            instruction=instruction,
        )