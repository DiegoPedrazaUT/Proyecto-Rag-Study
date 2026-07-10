import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.schemas.deck import DeckCreate, DeckDetail, DeckRead, DeckWithCount
from app.services.deck_service import DeckService
from app.schemas.llm import DeckFromDocumentRequest

router = APIRouter(prefix="/decks", tags=["decks"])


@router.post(
    "",
    response_model=DeckRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un mazo vacío",
    responses={
        201: {"description": "Mazo creado correctamente."},
        401: {"description": "Token ausente, inválido o expirado."},
        403: {"description": "El usuario no pertenece al salón indicado."},
        422: {"description": "Datos inválidos (por ejemplo, título vacío o organization_id mal formado)."},
        500: {"description": "Error interno del servidor."},
    },
)
async def create_deck(
    payload: DeckCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeckRead:
    """Crea un mazo de flashcards vacío dentro de un salón.

    El usuario debe pertenecer al `organization_id` indicado.
    """
    service = DeckService(db)
    deck = await service.create_empty_deck(payload=payload, current_user=current_user)
    return DeckRead.model_validate(deck)


@router.get(
    "",
    response_model=list[DeckWithCount],
    summary="Listar mis mazos",
    responses={
        200: {"description": "Lista de mazos del usuario (puede estar vacía)."},
        401: {"description": "Token ausente, inválido o expirado."},
        500: {"description": "Error interno del servidor."},
    },
)
async def list_decks(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DeckWithCount]:
    """Lista los mazos creados por el usuario autenticado.

    Cada mazo incluye `card_count`, el número de flashcards que contiene.
    """
    service = DeckService(db)
    return await service.list_user_decks(current_user=current_user)


@router.get(
    "/{deck_id}",
    response_model=DeckDetail,
    summary="Obtener un mazo con sus flashcards",
    responses={
        200: {"description": "Mazo con todas sus flashcards."},
        401: {"description": "Token ausente, inválido o expirado."},
        403: {"description": "El usuario no pertenece al salón del mazo."},
        404: {"description": "El mazo no existe."},
        422: {"description": "El deck_id de la URL no es un UUID válido."},
        500: {"description": "Error interno del servidor."},
    },
)
async def get_deck(
    deck_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeckDetail:
    """Devuelve un mazo y todas sus flashcards.

    Accesible para cualquier miembro del salón al que pertenece el mazo.
    """
    service = DeckService(db)
    return await service.get_deck_detail(deck_id=deck_id, current_user=current_user)


@router.delete(
    "/{deck_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un mazo completo",
    responses={
        204: {"description": "Mazo eliminado (junto con sus flashcards en cascada)."},
        401: {"description": "Token ausente, inválido o expirado."},
        403: {"description": "El usuario no es el dueño del mazo."},
        404: {"description": "El mazo no existe."},
        422: {"description": "El deck_id de la URL no es un UUID válido."},
        500: {"description": "Error interno del servidor."},
    },
)
async def delete_deck(
    deck_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Elimina un mazo y todas sus flashcards (borrado en cascada).

    Solo el dueño del mazo puede eliminarlo.
    """
    service = DeckService(db)
    await service.delete_deck(deck_id=deck_id, current_user=current_user)

@router.post(
    "/from-document",
    response_model=DeckDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Generar un mazo de flashcards desde un documento (IA)",
    responses={
        201: {"description": "Mazo generado con flashcards creadas por la IA."},
        401: {"description": "Token ausente, inválido o expirado."},
        403: {"description": "El usuario no pertenece al salón indicado."},
        404: {"description": "El documento no existe."},
        409: {"description": "El documento aún no está procesado (status != 'listo')."},
        422: {"description": "Datos inválidos o documento sin contenido."},
        500: {"description": "Error interno del servidor o de la LLM."},
    },
)

async def create_deck_from_document(
    payload: DeckFromDocumentRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeckDetail:
    """Genera un mazo de flashcards a partir de un documento procesado.

    Lee el contenido del documento, le pide a la IA que genere las flashcards,
    y crea el mazo en el salón indicado.
    """
    service = DeckService(db)
    deck = await service.create_deck_from_document(
        payload=payload, current_user=current_user
    )
    return DeckDetail.model_validate(deck)


@router.get(
    "/organization/{organization_id}",
    response_model=list[DeckWithCount],
    summary="Listar todos los mazos de un salón",
    responses={
        200: {"description": "Mazos del salón (visible para cualquier miembro)."},
        401: {"description": "Token ausente, inválido o expirado."},
        403: {"description": "El usuario no pertenece al salón."},
        422: {"description": "El organization_id no es un UUID válido."},
        500: {"description": "Error interno del servidor."},
    },
)
async def list_organization_decks(
    organization_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DeckWithCount]:
    """Lista todos los mazos creados en un salón, sin importar quién los creó.

    Accesible para cualquier miembro (accepted) del salón.
    """
    service = DeckService(db)
    return await service.list_organization_decks(
        organization_id=organization_id, current_user=current_user
    )