# [FILE] — app/domains/tasks/router.py
"""REST endpoints of the tasks domain.

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
    """Creates a task — 201; 404 missing project or assignee; 422 invalid enum."""
    # [STEP 1] Delegate to the service → project checked, assignee checked when provided
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
    """Deletes a task — 204 with no body, DB cascade downstream; 404 unknown id."""
    # [STEP 1] Delegate to the service → existence checked, row deleted
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
    """Fetches a task — 200; 404 if the id is unknown."""
    # [STEP 1] Delegate to the service → existence checked
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
    """Lists tasks — 200, page sorted by id; 422 if bounds are invalid."""
    # [STEP 1] Delegate to the service → bounded page, deterministic sort
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
    """Partially updates a task — 200; 404 task or assignee; 422 enum."""
    # [STEP 1] Delegate to the service → partial PATCH applied, explicit null unassigns
    return await services.update_task(db, data, task_id)
