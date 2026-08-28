# [FILE] — app/domains/comments/models.py
# [MODEL]
# synthesis: A Comment is not referenced by any table.
# entity: Comment
# table: comments
# columns: author_id, content, created_at, id, task_id, updated_at
# fks: author_id -> users.id [RESTRICT], task_id -> tasks.id [CASCADE]
# referenced_by: none
# [/MODEL]
"""SQLAlchemy model of the comments domain.

Last link of the relational graph, the most nested relation:
``task_id`` references ``tasks.id`` with ``ondelete=CASCADE`` (deleting
a task takes its comments with it — end of the containment axis
projects → tasks → comments, DB alone); ``author_id`` references
``users.id`` with ``ondelete=RESTRICT`` (a comment author cannot be
deleted — DB backstop of the application-level 409, D2). No
cross-domain ORM navigation (no ``relationship()`` in Phase 2).
"""

# ─── IMPORTS ───
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# ──────────────

# [CODE_START]


class Comment(Base):
    """Comment attached to a task, written by a user.

    Invariants:
    - ``task_id`` always points to an existing task: checked by the
      service (404 on write) and by the ``CASCADE`` FK — deleting the
      task takes the comment with it (never the reverse);
    - ``author_id`` always points to an existing user: checked by the
      service (404 on write); deleting the author is refused as long as
      the comment exists (application-level 409, ``RESTRICT`` FK as
      backstop — D2);
    - neither the task nor the author is modifiable after creation
      (Phase 2); ``content`` is never NULL.
    """

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    content: Mapped[str] = mapped_column(Text)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )
