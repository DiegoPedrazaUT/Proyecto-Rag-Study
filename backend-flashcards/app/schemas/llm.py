import uuid
from pydantic import BaseModel, Field


class LLMEditRequest(BaseModel):
    """Instrucción del usuario para editar una flashcard con la LLM."""

    instruction: str = Field(..., min_length=1, max_length=500)


class LLMEditProposal(BaseModel):
    """Propuesta de edición devuelta por la LLM (no se guarda todavía)."""

    front_text: str
    back_text: str

class GeneratedCard(BaseModel):
    """Una flashcard generada por la LLM."""

    front_text: str
    back_text: str


class GeneratedDeck(BaseModel):
    """Conjunto de flashcards generadas por la LLM."""

    cards: list[GeneratedCard]


class DeckFromDocumentRequest(BaseModel):
    """Petición para generar un mazo de flashcards desde un documento."""

    document_id: uuid.UUID
    organization_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=255)
    num_cards: int = Field(default=10, ge=1, le=35)