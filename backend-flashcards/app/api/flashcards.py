import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.schemas.flashcard import (
    FlashcardBulkCreate,
    FlashcardRead,
    FlashcardUpdate,
)
from app.services.flashcard_service import FlashcardService

router = APIRouter(prefix="/decks", tags=["flashcards"])


@router.post(
    "/{deck_id}/cards",
    response_model=list[FlashcardRead],
    status_code=status.HTTP_201_CREATED,
    summary="Agregar flashcards a un mazo",
    responses={
        201: {"description": "Flashcards agregadas correctamente."},
        401: {"description": "Token ausente, inválido o expirado."},
        403: {"description": "El usuario no es el dueño del mazo."},
        404: {"description": "El mazo no existe."},
        422: {"description": "Datos inválidos (lista vacía, o front/back vacíos)."},
        500: {"description": "Error interno del servidor."},
    },
)
async def add_cards(
    deck_id: uuid.UUID,
    payload: FlashcardBulkCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FlashcardRead]:
    """Agrega una o varias flashcards a un mazo existente.

    Solo el dueño del mazo puede agregar tarjetas.
    """
    service = FlashcardService(db)
    cards = await service.add_cards_to_deck(
        deck_id=deck_id, payload=payload, current_user=current_user
    )
    return [FlashcardRead.model_validate(c) for c in cards]


@router.patch(
    "/{deck_id}/cards/{card_id}",
    response_model=FlashcardRead,
    summary="Actualizar una flashcard",
    responses={
        200: {"description": "Flashcard actualizada correctamente."},
        401: {"description": "Token ausente, inválido o expirado."},
        403: {"description": "El usuario no es el dueño del mazo."},
        404: {"description": "El mazo no existe, o la flashcard no pertenece a ese mazo."},
        422: {"description": "Datos inválidos (ningún campo enviado, o campo vacío)."},
        500: {"description": "Error interno del servidor."},
    },
)
async def update_card(
    deck_id: uuid.UUID,
    card_id: uuid.UUID,
    payload: FlashcardUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FlashcardRead:
    """Actualiza el frente y/o reverso de una flashcard.

    Solo el dueño del mazo puede editar. La tarjeta debe pertenecer al mazo.
    """
    service = FlashcardService(db)
    card = await service.update_card(
        deck_id=deck_id,
        card_id=card_id,
        payload=payload,
        current_user=current_user,
    )
    return FlashcardRead.model_validate(card)


@router.delete(
    "/{deck_id}/cards/{card_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una flashcard",
    responses={
        204: {"description": "Flashcard eliminada correctamente."},
        401: {"description": "Token ausente, inválido o expirado."},
        403: {"description": "El usuario no es el dueño del mazo."},
        404: {"description": "El mazo no existe, o la flashcard no pertenece a ese mazo."},
        422: {"description": "El deck_id o card_id de la URL no es un UUID válido."},
        500: {"description": "Error interno del servidor."},
    },
)
async def delete_card(
    deck_id: uuid.UUID,
    card_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Elimina una flashcard de un mazo.

    Solo el dueño del mazo puede eliminar. La tarjeta debe pertenecer al mazo.
    """
    service = FlashcardService(db)
    await service.delete_card(
        deck_id=deck_id, card_id=card_id, current_user=current_user
    )