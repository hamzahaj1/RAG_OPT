# [FILE] — app/domains/tasks/models.py
# [MODEL]
# synthesis: A Task is referenced by comments.task_id (CASCADE — cascade-deleted).
# entity: Task
# table: tasks
# columns: assignee_id, created_at, description, id, priority, project_id, status, title, updated_at
# fks: assignee_id -> users.id [SET NULL], project_id -> projects.id [CASCADE]
# referenced_by: comments.task_id -> CASCADE
# [/MODEL]
"""SQLAlchemy model of the tasks domain.

First domain with a double cross-domain reference: ``project_id``
references ``projects.id`` with ``ondelete=CASCADE`` (deleting a
project takes its tasks with it — containment axis, DB alone);
``assignee_id`` references ``users.id`` with ``ondelete=SET NULL``
(deleting a user unassigns their tasks without destroying them — DB
alone, D2). No cross-domain ORM navigation (no ``relationship()`` in
Phase 2).
"""

# ─── IMPORTS ───
from datetime import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# ──────────────

# [CODE_START]


class TaskPriority(str, Enum):
    """Closed set of task priorities — persisted as ``String`` + CHECK (D1)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskStatus(str, Enum):
    """Closed set of task statuses — persisted as ``String`` + CHECK (D1)."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Task(Base):
    """Task attached to a project, assignable to a user.

    Invariants:
    - ``project_id`` always points to an existing project: checked by
      the service (404 on write) and by the ``CASCADE`` FK — deleting
      the project takes the task with it (never the reverse);
    - ``assignee_id`` is the only nullable FK of the phase: ``NULL``
      means "unassigned"; deleting the assignee resets ``NULL`` by the
      DB alone (``SET NULL``, D2);
    - ``status`` and ``priority`` are bounded to their enums by named
      CHECKs; ``description`` is never NULL (empty string by default).
    """

    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("priority IN ('low', 'medium', 'high')", name="priority"),
        CheckConstraint("status IN ('todo', 'in_progress', 'done')", name="status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assignee_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    description: Mapped[str] = mapped_column(Text, server_default="")
    priority: Mapped[str] = mapped_column(String(20), server_default=TaskPriority.MEDIUM.value)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), server_default=TaskStatus.TODO.value)
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )
