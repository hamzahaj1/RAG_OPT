# [FILE] — app/domains/projects/services.py
"""Business logic of the projects domain.

Carries every rule of the domain — routers remain thin wrappers:
organization existence checked by SELECT before any write (404, first
layer of D2 — the ``RESTRICT`` FK is the backstop), name uniqueness
**within the organization** (409, D14), 404 naming the entity and the
id. One write per HTTP request: ``commit`` then ``refresh`` here, never
in the routers.
"""

# ─── IMPORTS ───
from collections.abc import Sequence
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.projects.schemas import ProjectCreate, ProjectUpdate

# ──────────────

# [CODE_START]


# [RAG]
# signature: create_project(db: AsyncSession, data: ProjectCreate) -> Project
# tier: CORE
# weight: 2
# reads: organizations, projects
# mutates: projects
# calls: none
# called_by: projects.router.create_project, scripts.seed._ensure_project
# [/RAG]
async def create_project(db: AsyncSession, data: ProjectCreate) -> Project:
    """Creates a project.

    Business rules:
    - the organization must exist: SELECT on ``organizations`` before
      any write → 404 "Organization {id} not found" (D2);
    - the name is unique **within the organization** (D14): a duplicate
      there is refused with 409 — two distinct organizations may hold
      same-named projects.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    existing: Project | None
    organization: Organization | None
    project: Project
    # ─────────────────────────────────

    # [STEP 1] Check the organization's existence → no orphan FK will be written
    organization = await db.get(Organization, data.organization_id)
    if organization is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Organization {data.organization_id} not found"
        )

    # [STEP 2] Check name availability within the organization → no local duplicate
    existing = await db.scalar(
        select(Project).where(
            Project.organization_id == data.organization_id, Project.name == data.name
        )
    )
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Project name already taken in this organization"
        )

    # [STEP 3] Persist and refresh → id and server timestamps resolved
    project = Project(
        description=data.description, name=data.name, organization_id=data.organization_id
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


# [RAG]
# signature: delete_project(db: AsyncSession, project_id: int) -> None
# tier: LEAF
# weight: 2
# reads: none
# mutates: projects
# calls: projects.services.get_project
# called_by: projects.router.delete_project
# [/RAG]
async def delete_project(db: AsyncSession, project_id: int) -> None:
    """Deletes a project.

    Business rules:
    - unknown id → 404, no write;
    - the deletion cascades down to the tasks then their comments
      (Milestones 7–8) — carried by the DB alone (``ondelete=CASCADE``),
      never by an application-level SELECT.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    project: Project
    # ─────────────────────────────────

    # [STEP 1] Load the target project → 404 if absent
    project = await get_project(db, project_id)

    # [STEP 2] Delete and commit → the row no longer exists, DB cascade downstream
    await db.delete(project)
    await db.commit()


# [RAG]
# signature: get_project(db: AsyncSession, project_id: int) -> Project
# tier: CORE
# weight: 3
# reads: projects
# mutates: none
# calls: none
# called_by: projects.router.get_project, projects.services.delete_project,
#   projects.services.update_project
# [/RAG]
async def get_project(db: AsyncSession, project_id: int) -> Project:
    """Fetches a project by identifier.

    Business rules:
    - unknown id → 404 naming the entity and the id ("Project 42 not
      found"), error format shared by the five domains (FR-003).
    """
    # ─── VARIABLE DECLARATION ZONE ───
    project: Project | None
    # ─────────────────────────────────

    # [STEP 1] Load by primary key → project loaded or None
    project = await db.get(Project, project_id)

    # [STEP 2] Refuse absence → the output is guaranteed non-null
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Project {project_id} not found")
    return project


# [RAG]
# signature: list_projects(db: AsyncSession, limit: int, offset: int) -> Sequence[Project]
# tier: LEAF
# weight: 1
# reads: projects
# mutates: none
# calls: none
# called_by: projects.router.list_projects
# [/RAG]
async def list_projects(db: AsyncSession, limit: int, offset: int) -> Sequence[Project]:
    """Lists projects by page.

    Business rules:
    - sorted by ascending id: stable, deterministic pagination (D9);
    - bounds (1 ≤ limit ≤ 100, offset ≥ 0) validated upstream by the
      router — an empty list is a valid response, not an error.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    projects: Sequence[Project]
    # ─────────────────────────────────

    # [STEP 1] Load the requested page → sorted by id, bounds applied
    projects = (
        await db.scalars(select(Project).order_by(Project.id).limit(limit).offset(offset))
    ).all()
    return projects


# [RAG]
# signature: update_project(db: AsyncSession, data: ProjectUpdate, project_id: int) -> Project
# tier: LEAF
# weight: 2
# reads: projects
# mutates: projects
# calls: projects.services.get_project
# called_by: projects.router.update_project
# [/RAG]
async def update_project(db: AsyncSession, data: ProjectUpdate, project_id: int) -> Project:
    """Partially updates a project.

    Business rules:
    - ``exclude_unset`` semantics: only fields present in the body
      change — the organization is never modifiable (Phase 2);
    - a new name is subject to the same uniqueness **within the
      organization** as creation → 409 (D14);
    - unknown id → 404.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    existing: Project | None
    field: str
    project: Project
    update_data: dict[str, Any]
    value: Any
    # ─────────────────────────────────

    # [STEP 1] Load the target project → 404 if absent
    project = await get_project(db, project_id)

    # [STEP 2] Extract the fields actually provided → faithful partial PATCH
    update_data = data.model_dump(exclude_unset=True)

    # [STEP 3] Check the uniqueness of a new name within the organization → no local duplicate
    if "name" in update_data and update_data["name"] != project.name:
        existing = await db.scalar(
            select(Project).where(
                Project.organization_id == project.organization_id,
                Project.name == update_data["name"],
            )
        )
        if existing is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Project name already taken in this organization"
            )

    # [STEP 4] Apply the fields and persist → modification timestamp refreshed
    for field, value in update_data.items():
        setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    return project
