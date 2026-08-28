# [FILE] — app/domains/users/router.py
"""Endpoints REST du domaine users.

Cinq handlers homonymes des fonctions de service — wrappers minces sans
aucune logique : validation par Pydantic, règles métier dans
``services.py``, sérialisation par ``response_model``. Statuts et erreurs
conformes au contrat commun (POST 201, GET 200, PATCH 200, DELETE 204).
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
    """Crée un utilisateur — 201 ; 409 si l'email est déjà enregistré."""
    # [STEP 1] Déléguer au service → unicité vérifiée, mot de passe haché
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
    """Supprime un utilisateur — 204 sans corps ; 404 si l'id est inconnu."""
    # [STEP 1] Déléguer au service → existence vérifiée, ligne supprimée
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
    """Consulte un utilisateur — 200 ; 404 si l'id est inconnu."""
    # [STEP 1] Déléguer au service → existence vérifiée
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
    """Liste les utilisateurs — 200, page triée par id ; 422 si bornes invalides."""
    # [STEP 1] Déléguer au service → page bornée, tri déterministe
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
    """Modifie partiellement un utilisateur — 200 ; 404 id inconnu ; 409 email pris."""
    # [STEP 1] Déléguer au service → PATCH partiel appliqué, unicité vérifiée
    return await services.update_user(db, data, user_id)
