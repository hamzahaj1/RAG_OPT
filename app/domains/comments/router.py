# [FILE] — app/domains/comments/router.py
"""Endpoints REST du domaine comments.

Cinq handlers homonymes des fonctions de service — wrappers minces sans
aucune logique : validation par Pydantic, règles métier dans
``services.py``, sérialisation par ``response_model``. Statuts et erreurs
conformes au contrat commun (POST 201, GET 200, PATCH 200, DELETE 204) ;
particularité du domaine : ``task_id`` est un paramètre de requête
obligatoire sur la liste (FR-021, 422 s'il est absent).
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
# weight: 2
# tier: LEAF
# calls: comments.services.create_comment, core.database.get_db
# called_by: none
# reads: none
# mutates: none
# [/RAG]
@router.post("", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
async def create_comment(data: CommentCreate, db: AsyncSession = Depends(get_db)) -> Comment:
    """Crée un commentaire — 201 ; 404 tâche ou auteur inexistant."""
    # [STEP 1] Déléguer au service → tâche et auteur vérifiés avant écriture
    return await services.create_comment(db, data)


# [RAG]
# signature: delete_comment(comment_id: int, db: AsyncSession = Depends(get_db)) -> None
# weight: 2
# tier: LEAF
# calls: comments.services.delete_comment, core.database.get_db
# called_by: none
# reads: none
# mutates: none
# [/RAG]
@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(comment_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Supprime un commentaire — 204 sans corps ; 404 id inconnu."""
    # [STEP 1] Déléguer au service → existence vérifiée, ligne supprimée
    await services.delete_comment(db, comment_id)


# [RAG]
# signature: get_comment(comment_id: int, db: AsyncSession = Depends(get_db)) -> Comment
# weight: 2
# tier: LEAF
# calls: comments.services.get_comment, core.database.get_db
# called_by: none
# reads: none
# mutates: none
# [/RAG]
@router.get("/{comment_id}", response_model=CommentRead)
async def get_comment(comment_id: int, db: AsyncSession = Depends(get_db)) -> Comment:
    """Consulte un commentaire — 200 ; 404 si l'id est inconnu."""
    # [STEP 1] Déléguer au service → existence vérifiée
    return await services.get_comment(db, comment_id)


# [RAG]
# signature: list_comments(db: AsyncSession = Depends(get_db), limit: int = Query(default=50, ge=1,
#   le=100), offset: int = Query(default=0, ge=0), task_id: int = Query()) -> Sequence[Comment]
# weight: 2
# tier: LEAF
# calls: comments.services.list_comments, core.database.get_db
# called_by: none
# reads: none
# mutates: none
# [/RAG]
@router.get("", response_model=list[CommentRead])
async def list_comments(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    task_id: int = Query(),
) -> Sequence[Comment]:
    """Liste les commentaires d'une tâche — 200 ; 422 sans task_id ; 404 tâche inconnue."""
    # [STEP 1] Déléguer au service → tâche vérifiée, page filtrée et triée
    return await services.list_comments(db, limit, offset, task_id)


# [RAG]
# signature: update_comment(comment_id: int, data: CommentUpdate,
#   db: AsyncSession = Depends(get_db)) -> Comment
# weight: 2
# tier: LEAF
# calls: comments.services.update_comment, core.database.get_db
# called_by: none
# reads: none
# mutates: none
# [/RAG]
@router.patch("/{comment_id}", response_model=CommentRead)
async def update_comment(
    comment_id: int, data: CommentUpdate, db: AsyncSession = Depends(get_db)
) -> Comment:
    """Modifie partiellement un commentaire — 200 ; 404 id inconnu."""
    # [STEP 1] Déléguer au service → PATCH partiel appliqué, contenu seul modifiable
    return await services.update_comment(db, comment_id, data)
