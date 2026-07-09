import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FlashcardCreate(BaseModel):
    """Una flashcard a crear dentro de un mazo."""

    front_text: str = Field(..., min_length=1)
    back_text: str = Field(..., min_length=1)


class FlashcardBulkCreate(BaseModel):
    """Payload para agregar una o varias flashcards a un mazo."""

    cards: list[FlashcardCreate] = Field(..., min_length=1)


class FlashcardUpdate(BaseModel):
    """Campos editables de una flashcard. Al menos uno debe venir."""

    front_text: str | None = Field(default=None, min_length=1)
    back_text: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "FlashcardUpdate":
        if self.front_text is None and self.back_text is None:
            raise ValueError(
                "Debes enviar al menos uno: front_text o back_text."
            )
        return self


class FlashcardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    deck_id: uuid.UUID
    front_text: str
    back_text: str
    is_seen: bool
    created_at: datetime