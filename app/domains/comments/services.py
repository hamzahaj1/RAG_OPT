# [FILE] — app/domains/comments/services.py
"""Business logic of the comments domain.

Carries every rule of the domain — routers remain thin wrappers:
existence of the task and of the author checked by SELECT before any
write (404 naming the missing entity, first layer of D2 — the
``CASCADE``/``RESTRICT`` FKs are the backstop), listing always filtered
by an existing task (``task_id`` required, FR-021), 404 naming the
entity and the id. One write per HTTP request: ``commit`` then
``refresh`` here, never in the routers.
"""

# ─── IMPORTS ───
from collections.abc import Sequence
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.comments.models import Comment
from app.domains.comments.schemas import CommentCreate, CommentUpdate
from app.domains.tasks.models import Task
from app.domains.users.models import User

# ──────────────

# [CODE_START]


# [RAG]
# signature: create_comment(db: AsyncSession, data: CommentCreate) -> Comment
# tier: CORE
# weight: 2
# reads: tasks, users
# mutates: comments
# calls: none
# called_by: comments.router.create_comment, scripts.seed._ensure_comment
# [/RAG]
async def create_comment(db: AsyncSession, data: CommentCreate) -> Comment:
    """Creates a comment.

    Business rules:
    - the task must exist: SELECT on ``tasks`` before any write → 404
      "Task {id} not found" (D2);
    - the author must exist: SELECT on ``users`` before any write → 404
      "User {id} not found" (D2);
    - the task and the author are fixed at creation — neither is
      modifiable afterwards (Phase 2).
    """
    # ─── VARIABLE DECLARATION ZONE ───
    author: User | None
    comment: Comment
    task: Task | None
    # ─────────────────────────────────

    # [STEP 1] Check the task's existence → no orphan FK will be written
    task = await db.get(Task, data.task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Task {data.task_id} not found")

    # [STEP 2] Check the author's existence → valid attribution guaranteed
    author = await db.get(User, data.author_id)
    if author is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {data.author_id} not found")

    # [STEP 3] Persist and refresh → id and server timestamps resolved
    comment = Comment(
        author_id=data.author_id,
        content=data.content,
        task_id=data.task_id,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


# [RAG]
# signature: delete_comment(db: AsyncSession, comment_id: int) -> None
# tier: LEAF
# weight: 2
# reads: none
# mutates: comments
# calls: comments.services.get_comment
# called_by: comments.router.delete_comment
# [/RAG]
async def delete_comment(db: AsyncSession, comment_id: int) -> None:
    """Deletes a comment.

    Business rules:
    - unknown id → 404, no write;
    - leaf of the graph: no table references ``comments``, the deletion
      is a plain DELETE with no downstream check (D7).
    """
    # ─── VARIABLE DECLARATION ZONE ───
    comment: Comment
    # ─────────────────────────────────

    # [STEP 1] Load the target comment → 404 if absent
    comment = await get_comment(db, comment_id)

    # [STEP 2] Delete and commit → the row no longer exists
    await db.delete(comment)
    await db.commit()


# [RAG]
# signature: get_comment(db: AsyncSession, comment_id: int) -> Comment
# tier: CORE
# weight: 3
# reads: comments
# mutates: none
# calls: none
# called_by: comments.router.get_comment, comments.services.delete_comment,
#   comments.services.update_comment
# [/RAG]
async def get_comment(db: AsyncSession, comment_id: int) -> Comment:
    """Fetches a comment by identifier.

    Business rules:
    - unknown id → 404 naming the entity and the id ("Comment 42 not
      found"), error format shared by the five domains (FR-003).
    """
    # ─── VARIABLE DECLARATION ZONE ───
    comment: Comment | None
    # ─────────────────────────────────

    # [STEP 1] Load by primary key → comment loaded or None
    comment = await db.get(Comment, comment_id)

    # [STEP 2] Refuse absence → the output is guaranteed non-null
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Comment {comment_id} not found")
    return comment


# [RAG]
# signature: list_comments(db: AsyncSession, limit: int, offset: int,
#   task_id: int) -> Sequence[Comment]
# tier: LEAF
# weight: 1
# reads: comments, tasks
# mutates: none
# calls: none
# called_by: comments.router.list_comments
# [/RAG]
async def list_comments(
    db: AsyncSession, limit: int, offset: int, task_id: int
) -> Sequence[Comment]:
    """Lists the comments of a task by page.

    Business rules:
    - ``task_id`` is required and the task must exist → 404 "Task {id}
      not found" — never a global list of comments (FR-021);
    - only the comments of the requested task are returned;
    - sorted by ascending id: stable, deterministic pagination (D9);
    - bounds (1 ≤ limit ≤ 100, offset ≥ 0) validated upstream by the
      router — an empty list is a valid response, not an error.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    comments: Sequence[Comment]
    task: Task | None
    # ─────────────────────────────────

    # [STEP 1] Check the task's existence → the filter points to a real task
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Task {task_id} not found")

    # [STEP 2] Load the requested page → comments of that task only, sorted by id
    comments = (
        await db.scalars(
            select(Comment)
            .where(Comment.task_id == task_id)
            .order_by(Comment.id)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return comments


# [RAG]
# signature: update_comment(db: AsyncSession, comment_id: int, data: CommentUpdate) -> Comment
# tier: LEAF
# weight: 2
# reads: none
# mutates: comments
# calls: comments.services.get_comment
# called_by: comments.router.update_comment
# [/RAG]
async def update_comment(db: AsyncSession, comment_id: int, data: CommentUpdate) -> Comment:
    """Partially updates a comment.

    Business rules:
    - ``exclude_unset`` semantics: only a ``content`` present in the
      body changes — the task and the author are never modifiable
      (Phase 2);
    - unknown id → 404.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    comment: Comment
    field: str
    update_data: dict[str, Any]
    value: Any
    # ─────────────────────────────────

    # [STEP 1] Load the target comment → 404 if absent
    comment = await get_comment(db, comment_id)

    # [STEP 2] Extract the fields actually provided → faithful partial PATCH
    update_data = data.model_dump(exclude_unset=True)

    # [STEP 3] Apply the fields and persist → modification timestamp refreshed
    for field, value in update_data.items():
        setattr(comment, field, value)
    await db.commit()
    await db.refresh(comment)
    return comment
