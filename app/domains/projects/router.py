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


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)) -> Project:
    """Crée un projet — 201 ; 404 organisation inexistante ; 409 nom pris dans l'org."""
    # [STEP 1] Déléguer au service → organisation vérifiée, unicité locale vérifiée
    return await services.create_project(db, data)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Supprime un projet — 204 sans corps, cascade DB en aval ; 404 id inconnu."""
    # [STEP 1] Déléguer au service → existence vérifiée, ligne supprimée
    await services.delete_project(db, project_id)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)) -> Project:
    """Consulte un projet — 200 ; 404 si l'id est inconnu."""
    # [STEP 1] Déléguer au service → existence vérifiée
    return await services.get_project(db, project_id)


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Sequence[Project]:
    """Liste les projets — 200, page triée par id ; 422 si bornes invalides."""
    # [STEP 1] Déléguer au service → page bornée, tri déterministe
    return await services.list_projects(db, limit, offset)


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    data: ProjectUpdate, project_id: int, db: AsyncSession = Depends(get_db)
) -> Project:
    """Modifie partiellement un projet — 200 ; 404 id inconnu ; 409 nom pris dans l'org."""
    # [STEP 1] Déléguer au service → PATCH partiel appliqué, unicité locale vérifiée
    return await services.update_project(db, data, project_id)
