import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.flashcard import FlashcardRead


class DeckCreate(BaseModel):
    """Payload para crear un mazo vacío."""

    title: str = Field(..., min_length=1, max_length=255)
    organization_id: uuid.UUID
    document_id: uuid.UUID | None = None


class DeckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    organization_id: uuid.UUID
    document_id: uuid.UUID | None
    title: str
    created_at: datetime


class DeckWithCount(DeckRead):
    """Mazo con el número de flashcards que contiene (para listados)."""

    card_count: int


class DeckDetail(DeckRead):
    """Mazo con todas sus flashcards (para la vista de detalle)."""

    cards: list[FlashcardRead]