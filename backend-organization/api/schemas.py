from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=255, description="Descripción de la clase")
    subject: Optional[str] = Field(None, max_length=100, description="Asignatura")


class OrganizationCreate(OrganizationBase):
    pass 

class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    subject: Optional[str] = Field(None, max_length=100)

class OrganizationResponse(OrganizationBase):
    id: UUID
    career_id: int
    created_by: UUID
    join_code: str
    created_at: datetime
    class Config:
        from_attributes = True

class JoinOrganizationRequest(BaseModel):
    join_code: str = Field(..., min_length=5, max_length=20)

class MemberStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(accepted|rejected)$")

class MemberResponse(BaseModel):
    organization_id: UUID
    user_id: UUID
    role: str
    status: str
    joined_at: datetime
    class Config:
        from_attributes = True

# ¡NUEVO! Esquema combinado para que el Frontend vea nombres reales
class MemberWithUserResponse(MemberResponse):
    first_name: str
    last_name: str
    email: str

class InviteCreate(BaseModel):
    email: str

class InviteResponse(BaseModel):
    id: UUID
    organization_id: UUID
    email: str
    invited_by: UUID
    status: str
    created_at: datetime
    class Config:
        from_attributes = True

class JoinRequest(BaseModel):
    code: str