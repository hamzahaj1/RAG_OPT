# [FILE] — app/domains/tasks/services.py
"""Logique métier du domaine tasks.

Porte toutes les règles du domaine — les routeurs restent des wrappers
minces : existence du projet et, s'il est fourni, de l'assigné vérifiée
par SELECT avant toute écriture (404 nommant l'entité manquante, première
couche de D2 — les FK ``CASCADE``/``SET NULL`` sont le backstop), 404
nommant l'entité et l'id. Une écriture par requête HTTP : ``commit`` puis
``refresh`` ici, jamais dans les routeurs.
"""

# ─── IMPORTS ───
from collections.abc import Sequence
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.projects.models import Project
from app.domains.tasks.models import Task
from app.domains.tasks.schemas import TaskCreate, TaskUpdate
from app.domains.users.models import User

# ──────────────

# [CODE_START]


async def create_task(db: AsyncSession, data: TaskCreate) -> Task:
    """Crée une tâche.

    Règles métier :
    - le projet doit exister : SELECT sur ``projects`` avant toute
      écriture → 404 « Project {id} not found » (D2) ;
    - l'assigné est optionnel ; s'il est fourni, il doit exister →
      404 « User {id} not found » — une tâche naît non assignée quand
      ``assignee_id`` est absent ou ``null`` ;
    - ``status`` et ``priority`` hors enum sont refusés en 422 par
      Pydantic, en amont de ce service.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    assignee: User | None
    project: Project | None
    task: Task
    # ─────────────────────────────────────────

    # [STEP 1] Vérifier l'existence du projet → aucune FK orpheline ne sera écrite
    project = await db.get(Project, data.project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Project {data.project_id} not found")

    # [STEP 2] Vérifier l'assigné s'il est fourni → assignation valide ou tâche libre
    if data.assignee_id is not None:
        assignee = await db.get(User, data.assignee_id)
        if assignee is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {data.assignee_id} not found")

    # [STEP 3] Persister et rafraîchir → id et horodatages serveur résolus
    task = Task(
        assignee_id=data.assignee_id,
        description=data.description,
        priority=data.priority.value,
        project_id=data.project_id,
        status=data.status.value,
        title=data.title,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task_id: int) -> None:
    """Supprime une tâche.

    Règles métier :
    - id inconnu → 404, aucune écriture ;
    - la suppression descend en cascade vers les commentaires (Jalon 8) —
      portée par la DB seule (``ondelete=CASCADE``), jamais par un SELECT
      applicatif.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    task: Task
    # ─────────────────────────────────────────

    # [STEP 1] Charger la tâche cible → 404 si absente
    task = await get_task(db, task_id)

    # [STEP 2] Supprimer et valider → la ligne n'existe plus, cascade DB en aval
    await db.delete(task)
    await db.commit()


async def get_task(db: AsyncSession, task_id: int) -> Task:
    """Consulte une tâche par identifiant.

    Règles métier :
    - id inconnu → 404 nommant l'entité et l'id (« Task 42 not found »),
      format d'erreur commun aux cinq domaines (FR-003).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    task: Task | None
    # ─────────────────────────────────────────

    # [STEP 1] Charger par clé primaire → task chargée ou None
    task = await db.get(Task, task_id)

    # [STEP 2] Refuser l'absence → la sortie est garantie non nulle
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Task {task_id} not found")
    return task


async def list_tasks(db: AsyncSession, limit: int, offset: int) -> Sequence[Task]:
    """Liste les tâches par page.

    Règles métier :
    - tri par id croissant : pagination stable et déterministe (D9) ;
    - bornes (1 ≤ limit ≤ 100, offset ≥ 0) validées en amont par le
      routeur — une liste vide est une réponse valide, pas une erreur.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    tasks: Sequence[Task]
    # ─────────────────────────────────────────

    # [STEP 1] Charger la page demandée → tri par id, bornes appliquées
    tasks = (await db.scalars(select(Task).order_by(Task.id).limit(limit).offset(offset))).all()
    return tasks


async def update_task(db: AsyncSession, data: TaskUpdate, task_id: int) -> Task:
    """Modifie partiellement une tâche.

    Règles métier :
    - sémantique ``exclude_unset`` : seuls les champs présents dans le
      corps changent — le projet n'est jamais modifiable (Phase 2) ;
    - ``assignee_id`` distingue trois cas : champ absent (pas de
      changement), ``null`` explicite (désassignation, conservé par
      ``exclude_unset``), entier (assignation — l'assigné doit exister
      → 404) ;
    - id inconnu → 404.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    assignee: User | None
    field: str
    task: Task
    update_data: dict[str, Any]
    value: Any
    # ─────────────────────────────────────────

    # [STEP 1] Charger la tâche cible → 404 si absente
    task = await get_task(db, task_id)

    # [STEP 2] Extraire les champs réellement fournis → un null explicite est conservé
    update_data = data.model_dump(exclude_unset=True)

    # [STEP 3] Vérifier un nouvel assigné non nul → assignation valide ou désassignation
    if update_data.get("assignee_id") is not None:
        assignee = await db.get(User, update_data["assignee_id"])
        if assignee is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"User {update_data['assignee_id']} not found"
            )

    # [STEP 4] Appliquer les champs et persister → horodatage de modification rafraîchi
    for field, value in update_data.items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task
