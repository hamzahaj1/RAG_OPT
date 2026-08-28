# [FILE] — app/domains/comments/schemas.py
# [SCHEMA]
# synthesis: The 4 Pydantic schemas of the comments domain carry the contract of the Comment entity.
# domain: comments
# schemas: CommentBase(BaseModel), CommentCreate(CommentBase), CommentRead(CommentBase),
#   CommentUpdate(BaseModel)
# entity: Comment
# [/SCHEMA]
"""Pydantic schemas of the comments domain.

Pure data, no logic and no methods: four classes (Base, Create, Read,
Update) in alphabetical order. ``author_id`` and ``task_id`` only
appear on Create and Read — neither the task nor the author is
modifiable in Phase 2: Update only carries ``content``. ``content`` is
an unbounded ``Text``, aligned with the ``models.py`` column.
"""

# ─── IMPORTS ───
from datetime import datetime

from pydantic import BaseModel, ConfigDict

# ──────────────

# [CODE_START]


class CommentBase(BaseModel):
    """Fields shared by comment writes and reads."""

    content: str


class CommentCreate(CommentBase):
    """POST body — shared fields plus the task and the author (fixed)."""

    author_id: int
    task_id: int


class CommentRead(CommentBase):
    """API response — full state, task, author and timestamps."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    author_id: int
    task_id: int
    created_at: datetime
    updated_at: datetime


class CommentUpdate(BaseModel):
    """PATCH body — only ``content`` is modifiable, ``exclude_unset`` semantics."""

    content: str | None = None
