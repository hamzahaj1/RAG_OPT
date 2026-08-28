# [FILE] — app/domains/tasks/services.py
"""Business logic of the tasks domain.

Carries every rule of the domain — routers remain thin wrappers:
existence of the project and, when provided, of the assignee checked by
SELECT before any write (404 naming the missing entity, first layer of
D2 — the ``CASCADE``/``SET NULL`` FKs are the backstop), 404 naming the
entity and the id. One write per HTTP request: ``commit`` then
``refresh`` here, never in the routers.
"""

# ─── IMPORTS ───
from collections.abc import Sequence
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.projects.models import Project
from app.domains.tasks.models import Task
from app.domains.tasks.schemas import TaskCreate, TaskUpdate
from app.domains.users.models import User

# ──────────────

# [CODE_START]


# [RAG]
# signature: create_task(db: AsyncSession, data: TaskCreate) -> Task
# tier: CORE
# weight: 2
# reads: projects, users
# mutates: tasks
# calls: none
# called_by: scripts.seed._ensure_task, tasks.router.create_task
# [/RAG]
async def create_task(db: AsyncSession, data: TaskCreate) -> Task:
    """Creates a task.

    Business rules:
    - the project must exist: SELECT on ``projects`` before any write →
      404 "Project {id} not found" (D2);
    - the assignee is optional; when provided, it must exist → 404
      "User {id} not found" — a task is born unassigned when
      ``assignee_id`` is absent or ``null``;
    - ``status`` and ``priority`` outside their enums are refused with
      422 by Pydantic, upstream of this service.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    assignee: User | None
    project: Project | None
    task: Task
    # ─────────────────────────────────

    # [STEP 1] Check the project's existence → no orphan FK will be written
    project = await db.get(Project, data.project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Project {data.project_id} not found")

    # [STEP 2] Check the assignee when provided → valid assignment or free task
    if data.assignee_id is not None:
        assignee = await db.get(User, data.assignee_id)
        if assignee is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {data.assignee_id} not found")

    # [STEP 3] Persist and refresh → id and server timestamps resolved
    task = Task(
        assignee_id=data.assignee_id,
        description=data.description,
        priority=data.priority.value,
        project_id=data.project_id,
        status=data.status.value,
        title=data.title,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


# [RAG]
# signature: delete_task(db: AsyncSession, task_id: int) -> None
# tier: LEAF
# weight: 2
# reads: none
# mutates: tasks
# calls: tasks.services.get_task
# called_by: tasks.router.delete_task
# [/RAG]
async def delete_task(db: AsyncSession, task_id: int) -> None:
    """Deletes a task.

    Business rules:
    - unknown id → 404, no write;
    - the deletion cascades down to the comments (Milestone 8) —
      carried by the DB alone (``ondelete=CASCADE``), never by an
      application-level SELECT.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    task: Task
    # ─────────────────────────────────

    # [STEP 1] Load the target task → 404 if absent
    task = await get_task(db, task_id)

    # [STEP 2] Delete and commit → the row no longer exists, DB cascade downstream
    await db.delete(task)
    await db.commit()


# [RAG]
# signature: get_task(db: AsyncSession, task_id: int) -> Task
# tier: CORE
# weight: 3
# reads: tasks
# mutates: none
# calls: none
# called_by: tasks.router.get_task, tasks.services.delete_task, tasks.services.update_task
# [/RAG]
async def get_task(db: AsyncSession, task_id: int) -> Task:
    """Fetches a task by identifier.

    Business rules:
    - unknown id → 404 naming the entity and the id ("Task 42 not
      found"), error format shared by the five domains (FR-003).
    """
    # ─── VARIABLE DECLARATION ZONE ───
    task: Task | None
    # ─────────────────────────────────

    # [STEP 1] Load by primary key → task loaded or None
    task = await db.get(Task, task_id)

    # [STEP 2] Refuse absence → the output is guaranteed non-null
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Task {task_id} not found")
    return task


# [RAG]
# signature: list_tasks(db: AsyncSession, limit: int, offset: int) -> Sequence[Task]
# tier: LEAF
# weight: 1
# reads: tasks
# mutates: none
# calls: none
# called_by: tasks.router.list_tasks
# [/RAG]
async def list_tasks(db: AsyncSession, limit: int, offset: int) -> Sequence[Task]:
    """Lists tasks by page.

    Business rules:
    - sorted by ascending id: stable, deterministic pagination (D9);
    - bounds (1 ≤ limit ≤ 100, offset ≥ 0) validated upstream by the
      router — an empty list is a valid response, not an error.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    tasks: Sequence[Task]
    # ─────────────────────────────────

    # [STEP 1] Load the requested page → sorted by id, bounds applied
    tasks = (await db.scalars(select(Task).order_by(Task.id).limit(limit).offset(offset))).all()
    return tasks


# [RAG]
# signature: update_task(db: AsyncSession, data: TaskUpdate, task_id: int) -> Task
# tier: LEAF
# weight: 2
# reads: users
# mutates: tasks
# calls: tasks.services.get_task
# called_by: tasks.router.update_task
# [/RAG]
async def update_task(db: AsyncSession, data: TaskUpdate, task_id: int) -> Task:
    """Partially updates a task.

    Business rules:
    - ``exclude_unset`` semantics: only fields present in the body
      change — the project is never modifiable (Phase 2);
    - ``assignee_id`` distinguishes three cases: absent field (no
      change), explicit ``null`` (unassignment, preserved by
      ``exclude_unset``), integer (assignment — the assignee must
      exist → 404);
    - unknown id → 404.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    assignee: User | None
    field: str
    task: Task
    update_data: dict[str, Any]
    value: Any
    # ─────────────────────────────────

    # [STEP 1] Load the target task → 404 if absent
    task = await get_task(db, task_id)

    # [STEP 2] Extract the fields actually provided → an explicit null is preserved
    update_data = data.model_dump(exclude_unset=True)

    # [STEP 3] Check a new non-null assignee → valid assignment or unassignment
    if update_data.get("assignee_id") is not None:
        assignee = await db.get(User, update_data["assignee_id"])
        if assignee is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"User {update_data['assignee_id']} not found"
            )

    # [STEP 4] Apply the fields and persist → modification timestamp refreshed
    for field, value in update_data.items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task
