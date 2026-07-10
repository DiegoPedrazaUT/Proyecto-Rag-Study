from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.external import Organization, OrganizationMember
from app.schemas.organization import OrganizationRead

router = APIRouter(prefix="/my-organizations", tags=["organizations"])


@router.get(
    "",
    response_model=list[OrganizationRead],
    summary="Listar los salones a los que pertenezco",
    responses={
        200: {"description": "Lista de salones aceptados del usuario (puede estar vacía)."},
        401: {"description": "Token ausente, inválido o expirado."},
        500: {"description": "Error interno del servidor."},
    },
)
async def list_my_organizations(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OrganizationRead]:
    """Devuelve los salones donde el usuario es miembro con status 'accepted'.

    No incluye invitaciones pendientes. Útil para que el frontend sepa en qué
    salones el usuario puede crear mazos y quizzes.
    """
    stmt = (
        select(Organization)
        .join(
            OrganizationMember,
            OrganizationMember.organization_id == Organization.id,
        )
        .where(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.status == "accepted",
        )
    )
    result = await db.execute(stmt)
    organizations = result.scalars().all()
    return [OrganizationRead.model_validate(o) for o in organizations]