# [FILE] — app/domains/comments/services.py
"""Logique métier du domaine comments.

Porte toutes les règles du domaine — les routeurs restent des wrappers
minces : existence de la tâche et de l'auteur vérifiée par SELECT avant
toute écriture (404 nommant l'entité manquante, première couche de D2 —
les FK ``CASCADE``/``RESTRICT`` sont le backstop), liste toujours filtrée
par tâche existante (``task_id`` obligatoire, FR-021), 404 nommant
l'entité et l'id. Une écriture par requête HTTP : ``commit`` puis
``refresh`` ici, jamais dans les routeurs.
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
# weight: 2
# tier: CORE
# calls: none
# called_by: comments.router.create_comment, scripts.seed._ensure_comment
# reads: tasks, users
# mutates: comments
# [/RAG]
async def create_comment(db: AsyncSession, data: CommentCreate) -> Comment:
    """Crée un commentaire.

    Règles métier :
    - la tâche doit exister : SELECT sur ``tasks`` avant toute écriture
      → 404 « Task {id} not found » (D2) ;
    - l'auteur doit exister : SELECT sur ``users`` avant toute écriture
      → 404 « User {id} not found » (D2) ;
    - la tâche et l'auteur sont fixés à la création — aucun des deux
      n'est modifiable ensuite (Phase 2).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    author: User | None
    comment: Comment
    task: Task | None
    # ─────────────────────────────────────────

    # [STEP 1] Vérifier l'existence de la tâche → aucune FK orpheline ne sera écrite
    task = await db.get(Task, data.task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Task {data.task_id} not found")

    # [STEP 2] Vérifier l'existence de l'auteur → attribution valide garantie
    author = await db.get(User, data.author_id)
    if author is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {data.author_id} not found")

    # [STEP 3] Persister et rafraîchir → id et horodatages serveur résolus
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
# weight: 2
# tier: LEAF
# calls: comments.services.get_comment
# called_by: comments.router.delete_comment
# reads: none
# mutates: comments
# [/RAG]
async def delete_comment(db: AsyncSession, comment_id: int) -> None:
    """Supprime un commentaire.

    Règles métier :
    - id inconnu → 404, aucune écriture ;
    - feuille du graphe : aucune table ne référence ``comments``, la
      suppression est un DELETE simple sans vérification aval (D7).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    comment: Comment
    # ─────────────────────────────────────────

    # [STEP 1] Charger le commentaire cible → 404 si absent
    comment = await get_comment(db, comment_id)

    # [STEP 2] Supprimer et valider → la ligne n'existe plus
    await db.delete(comment)
    await db.commit()


# [RAG]
# signature: get_comment(db: AsyncSession, comment_id: int) -> Comment
# weight: 3
# tier: CORE
# calls: none
# called_by: comments.router.get_comment, comments.services.delete_comment,
#   comments.services.update_comment
# reads: comments
# mutates: none
# [/RAG]
async def get_comment(db: AsyncSession, comment_id: int) -> Comment:
    """Consulte un commentaire par identifiant.

    Règles métier :
    - id inconnu → 404 nommant l'entité et l'id (« Comment 42 not
      found »), format d'erreur commun aux cinq domaines (FR-003).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    comment: Comment | None
    # ─────────────────────────────────────────

    # [STEP 1] Charger par clé primaire → comment chargé ou None
    comment = await db.get(Comment, comment_id)

    # [STEP 2] Refuser l'absence → la sortie est garantie non nulle
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Comment {comment_id} not found")
    return comment


# [RAG]
# signature: list_comments(db: AsyncSession, limit: int, offset: int,
#   task_id: int) -> Sequence[Comment]
# weight: 1
# tier: LEAF
# calls: none
# called_by: comments.router.list_comments
# reads: comments, tasks
# mutates: none
# [/RAG]
async def list_comments(
    db: AsyncSession, limit: int, offset: int, task_id: int
) -> Sequence[Comment]:
    """Liste les commentaires d'une tâche par page.

    Règles métier :
    - ``task_id`` est obligatoire et la tâche doit exister → 404
      « Task {id} not found » — jamais de liste globale de commentaires
      (FR-021) ;
    - seuls les commentaires de la tâche demandée sont restitués ;
    - tri par id croissant : pagination stable et déterministe (D9) ;
    - bornes (1 ≤ limit ≤ 100, offset ≥ 0) validées en amont par le
      routeur — une liste vide est une réponse valide, pas une erreur.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    comments: Sequence[Comment]
    task: Task | None
    # ─────────────────────────────────────────

    # [STEP 1] Vérifier l'existence de la tâche → le filtre pointe une tâche réelle
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Task {task_id} not found")

    # [STEP 2] Charger la page demandée → commentaires de la tâche seule, tri par id
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
# weight: 2
# tier: LEAF
# calls: comments.services.get_comment
# called_by: comments.router.update_comment
# reads: none
# mutates: comments
# [/RAG]
async def update_comment(db: AsyncSession, comment_id: int, data: CommentUpdate) -> Comment:
    """Modifie partiellement un commentaire.

    Règles métier :
    - sémantique ``exclude_unset`` : seul un ``content`` présent dans le
      corps change — la tâche et l'auteur ne sont jamais modifiables
      (Phase 2) ;
    - id inconnu → 404.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    comment: Comment
    field: str
    update_data: dict[str, Any]
    value: Any
    # ─────────────────────────────────────────

    # [STEP 1] Charger le commentaire cible → 404 si absent
    comment = await get_comment(db, comment_id)

    # [STEP 2] Extraire les champs réellement fournis → PATCH partiel fidèle
    update_data = data.model_dump(exclude_unset=True)

    # [STEP 3] Appliquer les champs et persister → horodatage de modification rafraîchi
    for field, value in update_data.items():
        setattr(comment, field, value)
    await db.commit()
    await db.refresh(comment)
    return comment
