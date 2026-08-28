# [FILE] — app/domains/users/services.py
"""Business logic of the users domain.

Carries every rule of the domain — routers remain thin wrappers: email
uniqueness (409 before any write), bcrypt password hashing (cleartext
never persisted), 404 naming the entity and the id. One write per HTTP
request: ``commit`` then ``refresh`` here, never in the routers.
"""

# ─── IMPORTS ───
from collections.abc import Sequence
from typing import Any

import bcrypt
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.comments.models import Comment
from app.domains.organizations.models import Organization
from app.domains.users.models import User
from app.domains.users.schemas import UserCreate, UserUpdate

# ──────────────

# [CODE_START]


# [RAG]
# signature: _hash_password(password: str) -> str
# tier: CORE
# weight: 2
# reads: none
# mutates: none
# calls: none
# called_by: users.services.create_user, users.services.update_user
# [/RAG]
def _hash_password(password: str) -> str:
    """Derives the irreversible bcrypt fingerprint of a password (FR-009).

    Invariants:
    - a fresh salt is generated on every call: two calls on the same
      input produce two distinct fingerprints;
    - later comparison goes through bcrypt, never through equality.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    hashed: bytes
    # ─────────────────────────────────

    # [STEP 1] Hash with a fresh salt → self-salted fingerprint, ASCII-decodable
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


# [RAG]
# signature: create_user(db: AsyncSession, data: UserCreate) -> User
# tier: CORE
# weight: 3
# reads: users
# mutates: users
# calls: users.services._hash_password
# called_by: scripts.seed._ensure_user, users.router.create_user
# [/RAG]
async def create_user(db: AsyncSession, data: UserCreate) -> User:
    """Creates a user.

    Business rules:
    - the email is unique across the whole platform: a duplicate is
      refused with 409 before any write (FR-007);
    - only the bcrypt hash of the password is persisted (FR-009).
    """
    # ─── VARIABLE DECLARATION ZONE ───
    existing: User | None
    user: User
    # ─────────────────────────────────

    # [STEP 1] Check email availability → no duplicate will be written
    existing = await db.scalar(select(User).where(User.email == data.email))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    # [STEP 2] Build the user with the hash → the cleartext never leaves the request
    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=_hash_password(data.password),
        role=data.role.value,
    )

    # [STEP 3] Persist and refresh → id and server timestamps resolved
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# [RAG]
# signature: delete_user(db: AsyncSession, user_id: int) -> None
# tier: LEAF
# weight: 2
# reads: comments, organizations
# mutates: users
# calls: users.services.get_user
# called_by: users.router.delete_user
# [/RAG]
async def delete_user(db: AsyncSession, user_id: int) -> None:
    """Deletes a user.

    Business rules:
    - unknown id → 404, no write;
    - owner of at least one organization → 409 before any write
      (application-level SELECT, the ``RESTRICT`` FK remains the
      backstop — D2);
    - author of at least one comment → 409 before any write
      (application-level SELECT, the ``RESTRICT`` FK remains the
      backstop — D2);
    - task assignment never blocks: the DB unassigns on its own
      (``ondelete=SET NULL``, D2).
    """
    # ─── VARIABLE DECLARATION ZONE ───
    authored: Comment | None
    owned: Organization | None
    user: User
    # ─────────────────────────────────

    # [STEP 1] Load the target user → 404 if absent
    user = await get_user(db, user_id)

    # [STEP 2] Refuse an owner of organizations → no orphan FK possible
    owned = await db.scalar(select(Organization).where(Organization.owner_id == user_id))
    if owned is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"User {user_id} still owns organizations")

    # [STEP 3] Refuse an author of comments → attribution stays intact
    authored = await db.scalar(select(Comment).where(Comment.author_id == user_id))
    if authored is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"User {user_id} still has comments")

    # [STEP 4] Delete and commit → the row no longer exists
    await db.delete(user)
    await db.commit()


# [RAG]
# signature: get_user(db: AsyncSession, user_id: int) -> User
# tier: CORE
# weight: 3
# reads: users
# mutates: none
# calls: none
# called_by: users.router.get_user, users.services.delete_user, users.services.update_user
# [/RAG]
async def get_user(db: AsyncSession, user_id: int) -> User:
    """Fetches a user by identifier.

    Business rules:
    - unknown id → 404 naming the entity and the id ("User 42 not
      found"), error format shared by the five domains (FR-003).
    """
    # ─── VARIABLE DECLARATION ZONE ───
    user: User | None
    # ─────────────────────────────────

    # [STEP 1] Load by primary key → user loaded or None
    user = await db.get(User, user_id)

    # [STEP 2] Refuse absence → the output is guaranteed non-null
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {user_id} not found")
    return user


# [RAG]
# signature: list_users(db: AsyncSession, limit: int, offset: int) -> Sequence[User]
# tier: LEAF
# weight: 1
# reads: users
# mutates: none
# calls: none
# called_by: users.router.list_users
# [/RAG]
async def list_users(db: AsyncSession, limit: int, offset: int) -> Sequence[User]:
    """Lists users by page.

    Business rules:
    - sorted by ascending id: stable, deterministic pagination (D9);
    - bounds (1 ≤ limit ≤ 100, offset ≥ 0) validated upstream by the
      router — an empty list is a valid response, not an error.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    users: Sequence[User]
    # ─────────────────────────────────

    # [STEP 1] Load the requested page → sorted by id, bounds applied
    users = (await db.scalars(select(User).order_by(User.id).limit(limit).offset(offset))).all()
    return users


# [RAG]
# signature: update_user(db: AsyncSession, data: UserUpdate, user_id: int) -> User
# tier: LEAF
# weight: 3
# reads: users
# mutates: users
# calls: users.services._hash_password, users.services.get_user
# called_by: users.router.update_user
# [/RAG]
async def update_user(db: AsyncSession, data: UserUpdate, user_id: int) -> User:
    """Partially updates a user.

    Business rules:
    - ``exclude_unset`` semantics: only fields present in the body
      change, an absent field stays intact;
    - a new email is subject to the same uniqueness as creation → 409;
    - a new password is re-hashed, never persisted in cleartext;
    - unknown id → 404.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    existing: User | None
    field: str
    update_data: dict[str, Any]
    user: User
    value: Any
    # ─────────────────────────────────

    # [STEP 1] Load the target user → 404 if absent
    user = await get_user(db, user_id)

    # [STEP 2] Extract the fields actually provided → faithful partial PATCH
    update_data = data.model_dump(exclude_unset=True)

    # [STEP 3] Check the uniqueness of a new email → no duplicate will be written
    if "email" in update_data and update_data["email"] != user.email:
        existing = await db.scalar(select(User).where(User.email == update_data["email"]))
        if existing is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    # [STEP 4] Replace the password with its hash → the cleartext does not leave the step
    if "password" in update_data:
        update_data["hashed_password"] = _hash_password(str(update_data.pop("password")))

    # [STEP 5] Apply the fields and persist → modification timestamp refreshed
    for field, value in update_data.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user
