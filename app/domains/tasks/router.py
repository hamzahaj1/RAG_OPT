# [FILE] — app/domains/tasks/router.py
"""Endpoints REST du domaine tasks.

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
from app.domains.tasks import services
from app.domains.tasks.models import Task
from app.domains.tasks.schemas import TaskCreate, TaskRead, TaskUpdate

# ──────────────

# [CODE_START]

router = APIRouter(prefix="/tasks", tags=["tasks"])


# [RAG]
# signature: create_task(data: TaskCreate, db: AsyncSession = Depends(get_db)) -> Task
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: core.database.get_db, tasks.services.create_task
# called_by: none
# [/RAG]
@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(data: TaskCreate, db: AsyncSession = Depends(get_db)) -> Task:
    """Crée une tâche — 201 ; 404 projet ou assigné inexistant ; 422 enum invalide."""
    # [STEP 1] Déléguer au service → projet vérifié, assigné vérifié s'il est fourni
    return await services.create_task(db, data)


# [RAG]
# signature: delete_task(task_id: int, db: AsyncSession = Depends(get_db)) -> None
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: core.database.get_db, tasks.services.delete_task
# called_by: none
# [/RAG]
@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Supprime une tâche — 204 sans corps, cascade DB en aval ; 404 id inconnu."""
    # [STEP 1] Déléguer au service → existence vérifiée, ligne supprimée
    await services.delete_task(db, task_id)


# [RAG]
# signature: get_task(task_id: int, db: AsyncSession = Depends(get_db)) -> Task
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: core.database.get_db, tasks.services.get_task
# called_by: none
# [/RAG]
@router.get("/{task_id}", response_model=TaskRead)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)) -> Task:
    """Consulte une tâche — 200 ; 404 si l'id est inconnu."""
    # [STEP 1] Déléguer au service → existence vérifiée
    return await services.get_task(db, task_id)


# [RAG]
# signature: list_tasks(db: AsyncSession = Depends(get_db), limit: int = Query(default=50, ge=1,
#   le=100), offset: int = Query(default=0, ge=0)) -> Sequence[Task]
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: core.database.get_db, tasks.services.list_tasks
# called_by: none
# [/RAG]
@router.get("", response_model=list[TaskRead])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Sequence[Task]:
    """Liste les tâches — 200, page triée par id ; 422 si bornes invalides."""
    # [STEP 1] Déléguer au service → page bornée, tri déterministe
    return await services.list_tasks(db, limit, offset)


# [RAG]
# signature: update_task(data: TaskUpdate, task_id: int, db: AsyncSession = Depends(get_db)) -> Task
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: core.database.get_db, tasks.services.update_task
# called_by: none
# [/RAG]
@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(data: TaskUpdate, task_id: int, db: AsyncSession = Depends(get_db)) -> Task:
    """Modifie partiellement une tâche — 200 ; 404 tâche ou assigné ; 422 enum."""
    # [STEP 1] Déléguer au service → PATCH partiel appliqué, null explicite désassigne
    return await services.update_task(db, data, task_id)
