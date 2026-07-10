import uuid
from datetime import datetime
from pydantic import BaseModel


class FlashcardViewRead(BaseModel):
    """Una vista de flashcard, con el nombre de quien la vio."""

    user_id: uuid.UUID
    viewer_name: str
    viewed_at: datetime