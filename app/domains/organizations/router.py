# [FILE] — app/domains/organizations/router.py
"""Endpoints REST du domaine organizations.

Cinq handlers homonymes des fonctions de service — wrappers minces sans
aucune logique : validation par Pydantic, règles métier dans
``services.py``, sérialisation par ``response_model``. Statuts et erreurs
conformes au contrat commun (POST 201, GET 200, PATCH 200, DELETE 204).
"""

# ─── IMPORTS ───
from collections.abc import Sequence

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.organizations import services
from app.domains.organizations.models import Organization
from app.domains.organizations.schemas import (
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)

# ──────────────

# [CODE_START]

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate, db: AsyncSession = Depends(get_db)
) -> Organization:
    """Crée une organisation — 201 ; 404 owner inexistant ; 409 nom pris."""
    # [STEP 1] Déléguer au service → propriétaire vérifié, unicité du nom vérifiée
    return await services.create_organization(db, data)


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(organization_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Supprime une organisation — 204 sans corps ; 404 si l'id est inconnu."""
    # [STEP 1] Déléguer au service → existence vérifiée, ligne supprimée
    await services.delete_organization(db, organization_id)


@router.get("/{organization_id}", response_model=OrganizationRead)
async def get_organization(
    organization_id: int, db: AsyncSession = Depends(get_db)
) -> Organization:
    """Consulte une organisation — 200 ; 404 si l'id est inconnu."""
    # [STEP 1] Déléguer au service → existence vérifiée
    return await services.get_organization(db, organization_id)


@router.get("", response_model=list[OrganizationRead])
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Sequence[Organization]:
    """Liste les organisations — 200, page triée par id ; 422 si bornes invalides."""
    # [STEP 1] Déléguer au service → page bornée, tri déterministe
    return await services.list_organizations(db, limit, offset)


@router.patch("/{organization_id}", response_model=OrganizationRead)
async def update_organization(
    data: OrganizationUpdate, organization_id: int, db: AsyncSession = Depends(get_db)
) -> Organization:
    """Modifie partiellement une organisation — 200 ; 404 id inconnu ; 409 nom pris."""
    # [STEP 1] Déléguer au service → PATCH partiel appliqué, unicité vérifiée
    return await services.update_organization(db, data, organization_id)
