# [FILE] — app/domains/projects/router.py
"""Endpoints REST du domaine projects.

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
    """Crée un projet — 201 ; 404 organisation inexistante ; 409 nom pris dans l'org."""
    # [STEP 1] Déléguer au service → organisation vérifiée, unicité locale vérifiée
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
    """Supprime un projet — 204 sans corps, cascade DB en aval ; 404 id inconnu."""
    # [STEP 1] Déléguer au service → existence vérifiée, ligne supprimée
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
    """Consulte un projet — 200 ; 404 si l'id est inconnu."""
    # [STEP 1] Déléguer au service → existence vérifiée
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
    """Liste les projets — 200, page triée par id ; 422 si bornes invalides."""
    # [STEP 1] Déléguer au service → page bornée, tri déterministe
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
    """Modifie partiellement un projet — 200 ; 404 id inconnu ; 409 nom pris dans l'org."""
    # [STEP 1] Déléguer au service → PATCH partiel appliqué, unicité locale vérifiée
    return await services.update_project(db, data, project_id)
