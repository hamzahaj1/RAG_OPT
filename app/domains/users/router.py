# [FILE] — app/domains/users/router.py
"""REST endpoints of the users domain.

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
from app.domains.users import services
from app.domains.users.models import User
from app.domains.users.schemas import UserCreate, UserRead, UserUpdate

# ──────────────

# [CODE_START]

router = APIRouter(prefix="/users", tags=["users"])


# [RAG]
# signature: create_user(data: UserCreate, db: AsyncSession = Depends(get_db)) -> User
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: core.database.get_db, users.services.create_user
# called_by: none
# [/RAG]
@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    """Creates a user — 201; 409 if the email is already registered."""
    # [STEP 1] Delegate to the service → uniqueness checked, password hashed
    return await services.create_user(db, data)


# [RAG]
# signature: delete_user(user_id: int, db: AsyncSession = Depends(get_db)) -> None
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: core.database.get_db, users.services.delete_user
# called_by: none
# [/RAG]
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Deletes a user — 204 with no body; 404 if the id is unknown."""
    # [STEP 1] Delegate to the service → existence checked, row deleted
    await services.delete_user(db, user_id)


# [RAG]
# signature: get_user(user_id: int, db: AsyncSession = Depends(get_db)) -> User
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: core.database.get_db, users.services.get_user
# called_by: none
# [/RAG]
@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)) -> User:
    """Fetches a user — 200; 404 if the id is unknown."""
    # [STEP 1] Delegate to the service → existence checked
    return await services.get_user(db, user_id)


# [RAG]
# signature: list_users(db: AsyncSession = Depends(get_db), limit: int = Query(default=50, ge=1,
#   le=100), offset: int = Query(default=0, ge=0)) -> Sequence[User]
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: core.database.get_db, users.services.list_users
# called_by: none
# [/RAG]
@router.get("", response_model=list[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Sequence[User]:
    """Lists users — 200, page sorted by id; 422 if bounds are invalid."""
    # [STEP 1] Delegate to the service → bounded page, deterministic sort
    return await services.list_users(db, limit, offset)


# [RAG]
# signature: update_user(data: UserUpdate, user_id: int, db: AsyncSession = Depends(get_db)) -> User
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: core.database.get_db, users.services.update_user
# called_by: none
# [/RAG]
@router.patch("/{user_id}", response_model=UserRead)
async def update_user(data: UserUpdate, user_id: int, db: AsyncSession = Depends(get_db)) -> User:
    """Partially updates a user — 200; 404 unknown id; 409 email taken."""
    # [STEP 1] Delegate to the service → partial PATCH applied, uniqueness checked
    return await services.update_user(db, data, user_id)
