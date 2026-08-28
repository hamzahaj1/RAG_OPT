# [FILE] — app/domains/tasks/schemas.py
# [SCHEMA]
# synthesis: The 4 Pydantic schemas of the tasks domain carry the contract of the Task entity.
# domain: tasks
# schemas: TaskBase(BaseModel), TaskCreate(TaskBase), TaskRead(TaskBase), TaskUpdate(BaseModel)
# entity: Task
# [/SCHEMA]
"""Pydantic schemas of the tasks domain.

Pure data, no logic and no methods: four classes (Base, Create, Read,
Update) in alphabetical order. ``project_id`` only appears on Create
and Read — the project is not modifiable in Phase 2; ``assignee_id`` is
the only modifiable parent of the phase: present on Update, where an
explicit ``null`` unassigns while an absent field changes nothing
(``exclude_unset`` semantics). Maximum lengths are aligned with the
``models.py`` columns.
"""

# ─── IMPORTS ───
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domains.tasks.models import TaskPriority, TaskStatus

# ──────────────

# [CODE_START]


class TaskBase(BaseModel):
    """Fields shared by task writes and reads."""

    description: str = ""
    priority: TaskPriority
    status: TaskStatus
    title: str = Field(max_length=200)


class TaskCreate(TaskBase):
    """POST body — shared fields plus the project (fixed) and the optional assignee."""

    assignee_id: int | None = None
    project_id: int


class TaskRead(TaskBase):
    """API response — full state, project, optional assignee and timestamps."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    assignee_id: int | None
    project_id: int
    created_at: datetime
    updated_at: datetime


class TaskUpdate(BaseModel):
    """PATCH body — all fields optional, ``exclude_unset`` semantics.

    ``assignee_id`` distinguishes three cases: absent field (no
    change), explicit ``null`` (unassignment), integer (assignment).
    """

    assignee_id: int | None = None
    description: str | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    title: str | None = Field(default=None, max_length=200)
