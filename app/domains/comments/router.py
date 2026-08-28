# [FILE] — app/domains/comments/router.py
"""REST endpoints of the comments domain.

Five handlers homonymous with the service functions — thin wrappers
with no logic at all: validation by Pydantic, business rules in
``services.py``, serialization by ``response_model``. Statuses and
errors follow the shared contract (POST 201, GET 200, PATCH 200,
DELETE 204); domain particularity: ``task_id`` is a required query
parameter on the listing (FR-021, 422 when absent).
"""

# ─── IMPORTS ───
from collections.abc import Sequence

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.comments import services
from app.domains.comments.models import Comment
from app.domains.comments.schemas import CommentCreate, CommentRead, CommentUpdate

# ──────────────

# [CODE_START]

router = APIRouter(prefix="/comments", tags=["comments"])


# [RAG]
# signature: create_comment(data: CommentCreate, db: AsyncSession = Depends(get_db)) -> Comment
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: comments.services.create_comment, core.database.get_db
# called_by: none
# [/RAG]
@router.post("", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
async def create_comment(data: CommentCreate, db: AsyncSession = Depends(get_db)) -> Comment:
    """Creates a comment — 201; 404 missing task or author."""
    # [STEP 1] Delegate to the service → task and author checked before write
    return await services.create_comment(db, data)


# [RAG]
# signature: delete_comment(comment_id: int, db: AsyncSession = Depends(get_db)) -> None
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: comments.services.delete_comment, core.database.get_db
# called_by: none
# [/RAG]
@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(comment_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Deletes a comment — 204 with no body; 404 unknown id."""
    # [STEP 1] Delegate to the service → existence checked, row deleted
    await services.delete_comment(db, comment_id)


# [RAG]
# signature: get_comment(comment_id: int, db: AsyncSession = Depends(get_db)) -> Comment
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: comments.services.get_comment, core.database.get_db
# called_by: none
# [/RAG]
@router.get("/{comment_id}", response_model=CommentRead)
async def get_comment(comment_id: int, db: AsyncSession = Depends(get_db)) -> Comment:
    """Fetches a comment — 200; 404 if the id is unknown."""
    # [STEP 1] Delegate to the service → existence checked
    return await services.get_comment(db, comment_id)


# [RAG]
# signature: list_comments(db: AsyncSession = Depends(get_db), limit: int = Query(default=50, ge=1,
#   le=100), offset: int = Query(default=0, ge=0), task_id: int = Query()) -> Sequence[Comment]
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: comments.services.list_comments, core.database.get_db
# called_by: none
# [/RAG]
@router.get("", response_model=list[CommentRead])
async def list_comments(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    task_id: int = Query(),
) -> Sequence[Comment]:
    """Lists the comments of a task — 200; 422 without task_id; 404 unknown task."""
    # [STEP 1] Delegate to the service → task checked, page filtered and sorted
    return await services.list_comments(db, limit, offset, task_id)


# [RAG]
# signature: update_comment(comment_id: int, data: CommentUpdate,
#   db: AsyncSession = Depends(get_db)) -> Comment
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: comments.services.update_comment, core.database.get_db
# called_by: none
# [/RAG]
@router.patch("/{comment_id}", response_model=CommentRead)
async def update_comment(
    comment_id: int, data: CommentUpdate, db: AsyncSession = Depends(get_db)
) -> Comment:
    """Partially updates a comment — 200; 404 unknown id."""
    # [STEP 1] Delegate to the service → partial PATCH applied, content alone modifiable
    return await services.update_comment(db, comment_id, data)
