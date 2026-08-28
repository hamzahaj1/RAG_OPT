# [FILE] — app/domains/organizations/router.py
"""REST endpoints of the organizations domain.

Five handlers homonymous with the service functions — thin wrappers
with no logic at all: validation by Pydantic, business rules in
``services.py``, serialization by ``response_model``. Statuses and
errors follow the shared contract (POST 201, GET 200, PATCH 200,
DELETE 204).
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


# [RAG]
# signature: create_organization(data: OrganizationCreate,
#   db: AsyncSession = Depends(get_db)) -> Organization
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: core.database.get_db, organizations.services.create_organization
# called_by: none
# [/RAG]
@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate, db: AsyncSession = Depends(get_db)
) -> Organization:
    """Creates an organization — 201; 404 missing owner; 409 name taken."""
    # [STEP 1] Delegate to the service → owner checked, name uniqueness checked
    return await services.create_organization(db, data)


# [RAG]
# signature: delete_organization(organization_id: int, db: AsyncSession = Depends(get_db)) -> None
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: core.database.get_db, organizations.services.delete_organization
# called_by: none
# [/RAG]
@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(organization_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Deletes an organization — 204 with no body; 404 if the id is unknown."""
    # [STEP 1] Delegate to the service → existence checked, row deleted
    await services.delete_organization(db, organization_id)


# [RAG]
# signature: get_organization(organization_id: int,
#   db: AsyncSession = Depends(get_db)) -> Organization
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: core.database.get_db, organizations.services.get_organization
# called_by: none
# [/RAG]
@router.get("/{organization_id}", response_model=OrganizationRead)
async def get_organization(
    organization_id: int, db: AsyncSession = Depends(get_db)
) -> Organization:
    """Fetches an organization — 200; 404 if the id is unknown."""
    # [STEP 1] Delegate to the service → existence checked
    return await services.get_organization(db, organization_id)


# [RAG]
# signature: list_organizations(db: AsyncSession = Depends(get_db), limit: int = Query(default=50,
#   ge=1, le=100), offset: int = Query(default=0, ge=0)) -> Sequence[Organization]
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: core.database.get_db, organizations.services.list_organizations
# called_by: none
# [/RAG]
@router.get("", response_model=list[OrganizationRead])
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Sequence[Organization]:
    """Lists organizations — 200, page sorted by id; 422 if bounds are invalid."""
    # [STEP 1] Delegate to the service → bounded page, deterministic sort
    return await services.list_organizations(db, limit, offset)


# [RAG]
# signature: update_organization(data: OrganizationUpdate, organization_id: int,
#   db: AsyncSession = Depends(get_db)) -> Organization
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: core.database.get_db, organizations.services.update_organization
# called_by: none
# [/RAG]
@router.patch("/{organization_id}", response_model=OrganizationRead)
async def update_organization(
    data: OrganizationUpdate, organization_id: int, db: AsyncSession = Depends(get_db)
) -> Organization:
    """Partially updates an organization — 200; 404 unknown id; 409 name taken."""
    # [STEP 1] Delegate to the service → partial PATCH applied, uniqueness checked
    return await services.update_organization(db, data, organization_id)
