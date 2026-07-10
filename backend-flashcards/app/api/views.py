import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.schemas.flashcard import FlashcardRead
from app.schemas.view import FlashcardViewRead
from app.services.view_service import ViewService

router = APIRouter(prefix="/decks", tags=["views"])


@router.post(
    "/{deck_id}/cards/{card_id}/views",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Registrar que vi una flashcard",
    responses={
        204: {"description": "Vista registrada (o ya existía; es idempotente)."},
        401: {"description": "Token ausente, inválido o expirado."},
        403: {"description": "El usuario no pertenece al salón del mazo."},
        404: {"description": "El mazo no existe, o la flashcard no pertenece a ese mazo."},
        422: {"description": "El deck_id o card_id de la URL no es un UUID válido."},
        500: {"description": "Error interno del servidor."},
    },
)
async def register_view(
    deck_id: uuid.UUID,
    card_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Registra que el usuario actual vio esta flashcard.

    Accesible para cualquier miembro del salón. Idempotente: llamarlo
    varias veces no crea registros duplicados.
    """
    service = ViewService(db)
    await service.register_view(
        deck_id=deck_id, card_id=card_id, current_user=current_user
    )


@router.get(
    "/{deck_id}/cards/{card_id}/views",
    response_model=list[FlashcardViewRead],
    summary="Ver quién ha visto una flashcard",
    responses={
        200: {"description": "Lista de usuarios que han visto la flashcard."},
        401: {"description": "Token ausente, inválido o expirado."},
        403: {"description": "Solo el dueño del mazo puede consultar esta información."},
        404: {"description": "El mazo no existe, o la flashcard no pertenece a ese mazo."},
        422: {"description": "El deck_id o card_id de la URL no es un UUID válido."},
        500: {"description": "Error interno del servidor."},
    },
)
async def list_card_views(
    deck_id: uuid.UUID,
    card_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FlashcardViewRead]:
    """Lista los usuarios que han visto esta flashcard.

    Solo el dueño del mazo puede consultar esta información.
    """
    service = ViewService(db)
    views = await service.list_card_views(
        deck_id=deck_id, card_id=card_id, current_user=current_user
    )
    return [FlashcardViewRead.model_validate(v) for v in views]


@router.get(
    "/{deck_id}/unseen",
    response_model=list[FlashcardRead],
    summary="Flashcards del mazo que aún no he visto",
    responses={
        200: {"description": "Lista de flashcards del mazo que el usuario no ha visto."},
        401: {"description": "Token ausente, inválido o expirado."},
        403: {"description": "El usuario no pertenece al salón del mazo."},
        404: {"description": "El mazo no existe."},
        422: {"description": "El deck_id de la URL no es un UUID válido."},
        500: {"description": "Error interno del servidor."},
    },
)
async def list_unseen(
    deck_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FlashcardRead]:
    """Lista las flashcards del mazo que el usuario actual aún no ha visto.

    Accesible para cualquier miembro del salón.
    """
    service = ViewService(db)
    cards = await service.list_unseen(deck_id=deck_id, current_user=current_user)
    return [FlashcardRead.model_validate(c) for c in cards]