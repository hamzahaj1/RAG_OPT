# [FILE] — app/domains/projects/router.py
"""REST endpoints of the projects domain.

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
from app.domains.projects import services
from app.domains.projects.models import Project
from app.domains.projects.schemas import ProjectCreate, ProjectRead, ProjectUpdate

# ──────────────

# [CODE_START]

router = APIRouter(prefix="/projects", tags=["projects"])


# [RAG]
# signature: create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)) -> Project
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: core.database.get_db, projects.services.create_project
# called_by: none
# [/RAG]
@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)) -> Project:
    """Creates a project — 201; 404 missing organization; 409 name taken in the org."""
    # [STEP 1] Delegate to the service → organization checked, local uniqueness checked
    return await services.create_project(db, data)


# [RAG]
# signature: delete_project(project_id: int, db: AsyncSession = Depends(get_db)) -> None
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: core.database.get_db, projects.services.delete_project
# called_by: none
# [/RAG]
@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Deletes a project — 204 with no body, DB cascade downstream; 404 unknown id."""
    # [STEP 1] Delegate to the service → existence checked, row deleted
    await services.delete_project(db, project_id)


# [RAG]
# signature: get_project(project_id: int, db: AsyncSession = Depends(get_db)) -> Project
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: core.database.get_db, projects.services.get_project
# called_by: none
# [/RAG]
@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)) -> Project:
    """Fetches a project — 200; 404 if the id is unknown."""
    # [STEP 1] Delegate to the service → existence checked
    return await services.get_project(db, project_id)


# [RAG]
# signature: list_projects(db: AsyncSession = Depends(get_db), limit: int = Query(default=50, ge=1,
#   le=100), offset: int = Query(default=0, ge=0)) -> Sequence[Project]
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: core.database.get_db, projects.services.list_projects
# called_by: none
# [/RAG]
@router.get("", response_model=list[ProjectRead])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Sequence[Project]:
    """Lists projects — 200, page sorted by id; 422 if bounds are invalid."""
    # [STEP 1] Delegate to the service → bounded page, deterministic sort
    return await services.list_projects(db, limit, offset)


# [RAG]
# signature: update_project(data: ProjectUpdate, project_id: int,
#   db: AsyncSession = Depends(get_db)) -> Project
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: core.database.get_db, projects.services.update_project
# called_by: none
# [/RAG]
@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    data: ProjectUpdate, project_id: int, db: AsyncSession = Depends(get_db)
) -> Project:
    """Partially updates a project — 200; 404 unknown id; 409 name taken in the org."""
    # [STEP 1] Delegate to the service → partial PATCH applied, local uniqueness checked
    return await services.update_project(db, data, project_id)
