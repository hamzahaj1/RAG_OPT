# [FILE] — app/domains/organizations/services.py
"""Business logic of the organizations domain.

Carries every rule of the domain — routers remain thin wrappers: owner
existence checked by SELECT before any write (404, first layer of D2 —
the ``RESTRICT`` FK is the backstop), name uniqueness (409), 404 naming
the entity and the id. One write per HTTP request: ``commit`` then
``refresh`` here, never in the routers.
"""

# ─── IMPORTS ───
from collections.abc import Sequence
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.organizations.models import Organization
from app.domains.organizations.schemas import OrganizationCreate, OrganizationUpdate
from app.domains.projects.models import Project
from app.domains.users.models import User

# ──────────────

# [CODE_START]


# [RAG]
# signature: create_organization(db: AsyncSession, data: OrganizationCreate) -> Organization
# tier: CORE
# weight: 2
# reads: organizations, users
# mutates: organizations
# calls: none
# called_by: organizations.router.create_organization, scripts.seed._ensure_organization
# [/RAG]
async def create_organization(db: AsyncSession, data: OrganizationCreate) -> Organization:
    """Creates an organization.

    Business rules:
    - the owner must exist: SELECT on ``users`` before any write → 404
      "User {id} not found" (FR-011, D2);
    - the name is unique across the whole platform: a duplicate is
      refused with 409 before any write (FR-012).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    existing: Organization | None
    organization: Organization
    owner: User | None
    # ─────────────────────────────────────────

    # [STEP 1] Check the owner's existence → no orphan FK will be written
    owner = await db.get(User, data.owner_id)
    if owner is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {data.owner_id} not found")

    # [STEP 2] Check name availability → no duplicate will be written
    existing = await db.scalar(select(Organization).where(Organization.name == data.name))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Organization name already taken")

    # [STEP 3] Persist and refresh → id and server timestamps resolved
    organization = Organization(name=data.name, owner_id=data.owner_id)
    db.add(organization)
    await db.commit()
    await db.refresh(organization)
    return organization


# [RAG]
# signature: delete_organization(db: AsyncSession, organization_id: int) -> None
# tier: LEAF
# weight: 2
# reads: projects
# mutates: organizations
# calls: organizations.services.get_organization
# called_by: organizations.router.delete_organization
# [/RAG]
async def delete_organization(db: AsyncSession, organization_id: int) -> None:
    """Deletes an organization.

    Business rules:
    - unknown id → 404, no write;
    - organization holding at least one project → 409 before any write
      (application-level SELECT, the ``RESTRICT`` FK remains the
      backstop — D2): the deletion is blocked by the projects, never
      propagated to them.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    held: Project | None
    organization: Organization
    # ─────────────────────────────────────────

    # [STEP 1] Load the target organization → 404 if absent
    organization = await get_organization(db, organization_id)

    # [STEP 2] Refuse an occupied organization → no orphan FK possible
    held = await db.scalar(select(Project).where(Project.organization_id == organization_id))
    if held is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Organization {organization_id} still has projects"
        )

    # [STEP 3] Delete and commit → the row no longer exists
    await db.delete(organization)
    await db.commit()


# [RAG]
# signature: get_organization(db: AsyncSession, organization_id: int) -> Organization
# tier: CORE
# weight: 3
# reads: organizations
# mutates: none
# calls: none
# called_by: organizations.router.get_organization, organizations.services.delete_organization,
#   organizations.services.update_organization
# [/RAG]
async def get_organization(db: AsyncSession, organization_id: int) -> Organization:
    """Fetches an organization by identifier.

    Business rules:
    - unknown id → 404 naming the entity and the id ("Organization 42
      not found"), error format shared by the five domains (FR-003).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    organization: Organization | None
    # ─────────────────────────────────────────

    # [STEP 1] Load by primary key → organization loaded or None
    organization = await db.get(Organization, organization_id)

    # [STEP 2] Refuse absence → the output is guaranteed non-null
    if organization is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Organization {organization_id} not found")
    return organization


# [RAG]
# signature: list_organizations(db: AsyncSession, limit: int, offset: int) -> Sequence[Organization]
# tier: LEAF
# weight: 1
# reads: organizations
# mutates: none
# calls: none
# called_by: organizations.router.list_organizations
# [/RAG]
async def list_organizations(db: AsyncSession, limit: int, offset: int) -> Sequence[Organization]:
    """Lists organizations by page.

    Business rules:
    - sorted by ascending id: stable, deterministic pagination (D9);
    - bounds (1 ≤ limit ≤ 100, offset ≥ 0) validated upstream by the
      router — an empty list is a valid response, not an error.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    organizations: Sequence[Organization]
    # ─────────────────────────────────────────

    # [STEP 1] Load the requested page → sorted by id, bounds applied
    organizations = (
        await db.scalars(select(Organization).order_by(Organization.id).limit(limit).offset(offset))
    ).all()
    return organizations


# [RAG]
# signature: update_organization(db: AsyncSession, data: OrganizationUpdate,
#   organization_id: int) -> Organization
# tier: LEAF
# weight: 2
# reads: organizations
# mutates: organizations
# calls: organizations.services.get_organization
# called_by: organizations.router.update_organization
# [/RAG]
async def update_organization(
    db: AsyncSession, data: OrganizationUpdate, organization_id: int
) -> Organization:
    """Partially updates an organization.

    Business rules:
    - ``exclude_unset`` semantics: only fields present in the body
      change — the owner is never modifiable (Phase 2);
    - a new name is subject to the same uniqueness as creation → 409;
    - unknown id → 404.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    existing: Organization | None
    field: str
    organization: Organization
    update_data: dict[str, Any]
    value: Any
    # ─────────────────────────────────────────

    # [STEP 1] Load the target organization → 404 if absent
    organization = await get_organization(db, organization_id)

    # [STEP 2] Extract the fields actually provided → faithful partial PATCH
    update_data = data.model_dump(exclude_unset=True)

    # [STEP 3] Check the uniqueness of a new name → no duplicate will be written
    if "name" in update_data and update_data["name"] != organization.name:
        existing = await db.scalar(
            select(Organization).where(Organization.name == update_data["name"])
        )
        if existing is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Organization name already taken")

    # [STEP 4] Apply the fields and persist → modification timestamp refreshed
    for field, value in update_data.items():
        setattr(organization, field, value)
    await db.commit()
    await db.refresh(organization)
    return organization
