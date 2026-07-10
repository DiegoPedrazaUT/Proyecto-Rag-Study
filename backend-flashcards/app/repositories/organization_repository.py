import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.external import OrganizationMember


class OrganizationRepository:
    """Acceso de solo lectura a la membresía de salones."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def is_member(
        self, *, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> bool:
        """True si el usuario es miembro ACEPTADO del salón."""
        stmt = (
            select(func.count())
            .select_from(OrganizationMember)
            .where(
                OrganizationMember.user_id == user_id,
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.status == "accepted",
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one() > 0