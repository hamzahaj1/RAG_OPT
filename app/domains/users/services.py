# [FILE] — app/domains/users/services.py
"""Logique métier du domaine users.

Porte toutes les règles du domaine — les routeurs restent des wrappers
minces : unicité de l'email (409 avant toute écriture), hachage bcrypt du
mot de passe (jamais de clair persisté), 404 nommant l'entité et l'id.
Une écriture par requête HTTP : ``commit`` puis ``refresh`` ici, jamais
dans les routeurs.
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
    """Dérive l'empreinte bcrypt irréversible d'un mot de passe (FR-009).

    Invariants :
    - un sel frais est généré à chaque appel : deux appels sur la même
      entrée produisent deux empreintes distinctes ;
    - la comparaison ultérieure passe par bcrypt, jamais par égalité.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    hashed: bytes
    # ─────────────────────────────────────────

    # [STEP 1] Hacher avec un sel frais → empreinte auto-salée, décodable en ASCII
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
    """Crée un utilisateur.

    Règles métier :
    - l'email est unique sur toute la plateforme : un doublon est refusé
      en 409 avant toute écriture (FR-007) ;
    - seul le hash bcrypt du mot de passe est persisté (FR-009).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    existing: User | None
    user: User
    # ─────────────────────────────────────────

    # [STEP 1] Vérifier la disponibilité de l'email → aucun doublon ne sera écrit
    existing = await db.scalar(select(User).where(User.email == data.email))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    # [STEP 2] Construire l'utilisateur avec le hash → le clair ne quitte pas la requête
    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=_hash_password(data.password),
        role=data.role.value,
    )

    # [STEP 3] Persister et rafraîchir → id et horodatages serveur résolus
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
    """Supprime un utilisateur.

    Règles métier :
    - id inconnu → 404, aucune écriture ;
    - propriétaire d'au moins une organisation → 409 avant toute écriture
      (SELECT applicatif, la FK ``RESTRICT`` reste le backstop — D2) ;
    - auteur d'au moins un commentaire → 409 avant toute écriture
      (SELECT applicatif, la FK ``RESTRICT`` reste le backstop — D2) ;
    - l'assignation de tâches ne bloque jamais : la DB désassigne seule
      (``ondelete=SET NULL``, D2).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    authored: Comment | None
    owned: Organization | None
    user: User
    # ─────────────────────────────────────────

    # [STEP 1] Charger l'utilisateur cible → 404 si absent
    user = await get_user(db, user_id)

    # [STEP 2] Refuser un propriétaire d'organisations → aucune FK orpheline possible
    owned = await db.scalar(select(Organization).where(Organization.owner_id == user_id))
    if owned is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"User {user_id} still owns organizations")

    # [STEP 3] Refuser un auteur de commentaires → l'attribution reste intègre
    authored = await db.scalar(select(Comment).where(Comment.author_id == user_id))
    if authored is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"User {user_id} still has comments")

    # [STEP 4] Supprimer et valider → la ligne n'existe plus
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
    """Consulte un utilisateur par identifiant.

    Règles métier :
    - id inconnu → 404 nommant l'entité et l'id (« User 42 not found »),
      format d'erreur commun aux cinq domaines (FR-003).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    user: User | None
    # ─────────────────────────────────────────

    # [STEP 1] Charger par clé primaire → user chargé ou None
    user = await db.get(User, user_id)

    # [STEP 2] Refuser l'absence → la sortie est garantie non nulle
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
    """Liste les utilisateurs par page.

    Règles métier :
    - tri par id croissant : pagination stable et déterministe (D9) ;
    - bornes (1 ≤ limit ≤ 100, offset ≥ 0) validées en amont par le
      routeur — une liste vide est une réponse valide, pas une erreur.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    users: Sequence[User]
    # ─────────────────────────────────────────

    # [STEP 1] Charger la page demandée → tri par id, bornes appliquées
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
    """Modifie partiellement un utilisateur.

    Règles métier :
    - sémantique ``exclude_unset`` : seuls les champs présents dans le
      corps changent, un champ absent reste intact ;
    - un nouvel email est soumis à la même unicité que la création → 409 ;
    - un nouveau mot de passe est re-haché, jamais persisté en clair ;
    - id inconnu → 404.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    existing: User | None
    field: str
    update_data: dict[str, Any]
    user: User
    value: Any
    # ─────────────────────────────────────────

    # [STEP 1] Charger l'utilisateur cible → 404 si absent
    user = await get_user(db, user_id)

    # [STEP 2] Extraire les champs réellement fournis → PATCH partiel fidèle
    update_data = data.model_dump(exclude_unset=True)

    # [STEP 3] Vérifier l'unicité d'un nouvel email → aucun doublon ne sera écrit
    if "email" in update_data and update_data["email"] != user.email:
        existing = await db.scalar(select(User).where(User.email == update_data["email"]))
        if existing is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    # [STEP 4] Remplacer le mot de passe par son hash → le clair ne sort pas de l'étape
    if "password" in update_data:
        update_data["hashed_password"] = _hash_password(str(update_data.pop("password")))

    # [STEP 5] Appliquer les champs et persister → horodatage de modification rafraîchi
    for field, value in update_data.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user
