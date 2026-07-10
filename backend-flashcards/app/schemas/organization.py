import uuid
from pydantic import BaseModel, ConfigDict


class OrganizationRead(BaseModel):
    """Un salón al que pertenece el usuario."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    subject: str | None