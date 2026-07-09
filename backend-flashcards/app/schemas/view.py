import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FlashcardViewRead(BaseModel):
    """Una vista registrada: quién vio una tarjeta y cuándo."""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    flashcard_id: uuid.UUID
    viewed_at: datetime