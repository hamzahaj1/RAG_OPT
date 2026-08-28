# [FILE] — app/domains/projects/services.py
"""Logique métier du domaine projects.

Porte toutes les règles du domaine — les routeurs restent des wrappers
minces : existence de l'organisation vérifiée par SELECT avant toute
écriture (404, première couche de D2 — la FK ``RESTRICT`` est le
backstop), unicité du nom **dans l'organisation** (409, D14), 404
nommant l'entité et l'id. Une écriture par requête HTTP : ``commit``
puis ``refresh`` ici, jamais dans les routeurs.
"""

# ─── IMPORTS ───
from collections.abc import Sequence
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.projects.schemas import ProjectCreate, ProjectUpdate

# ──────────────

# [CODE_START]


# [RAG]
# signature: create_project(db: AsyncSession, data: ProjectCreate) -> Project
# tier: CORE
# weight: 2
# reads: organizations, projects
# mutates: projects
# calls: none
# called_by: projects.router.create_project, scripts.seed._ensure_project
# [/RAG]
async def create_project(db: AsyncSession, data: ProjectCreate) -> Project:
    """Crée un projet.

    Règles métier :
    - l'organisation doit exister : SELECT sur ``organizations`` avant
      toute écriture → 404 « Organization {id} not found » (D2) ;
    - le nom est unique **au sein de l'organisation** (D14) : un doublon
      y est refusé en 409 — deux organisations distinctes peuvent porter
      des projets homonymes.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    existing: Project | None
    organization: Organization | None
    project: Project
    # ─────────────────────────────────────────

    # [STEP 1] Vérifier l'existence de l'organisation → aucune FK orpheline ne sera écrite
    organization = await db.get(Organization, data.organization_id)
    if organization is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Organization {data.organization_id} not found"
        )

    # [STEP 2] Vérifier la disponibilité du nom dans l'organisation → aucun doublon local
    existing = await db.scalar(
        select(Project).where(
            Project.organization_id == data.organization_id, Project.name == data.name
        )
    )
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Project name already taken in this organization"
        )

    # [STEP 3] Persister et rafraîchir → id et horodatages serveur résolus
    project = Project(
        description=data.description, name=data.name, organization_id=data.organization_id
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


# [RAG]
# signature: delete_project(db: AsyncSession, project_id: int) -> None
# tier: LEAF
# weight: 2
# reads: none
# mutates: projects
# calls: projects.services.get_project
# called_by: projects.router.delete_project
# [/RAG]
async def delete_project(db: AsyncSession, project_id: int) -> None:
    """Supprime un projet.

    Règles métier :
    - id inconnu → 404, aucune écriture ;
    - la suppression descend en cascade vers les tâches puis leurs
      commentaires (Jalons 7–8) — portée par la DB seule
      (``ondelete=CASCADE``), jamais par un SELECT applicatif.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    project: Project
    # ─────────────────────────────────────────

    # [STEP 1] Charger le projet cible → 404 si absent
    project = await get_project(db, project_id)

    # [STEP 2] Supprimer et valider → la ligne n'existe plus, cascade DB en aval
    await db.delete(project)
    await db.commit()


# [RAG]
# signature: get_project(db: AsyncSession, project_id: int) -> Project
# tier: CORE
# weight: 3
# reads: projects
# mutates: none
# calls: none
# called_by: projects.router.get_project, projects.services.delete_project,
#   projects.services.update_project
# [/RAG]
async def get_project(db: AsyncSession, project_id: int) -> Project:
    """Consulte un projet par identifiant.

    Règles métier :
    - id inconnu → 404 nommant l'entité et l'id (« Project 42 not
      found »), format d'erreur commun aux cinq domaines (FR-003).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    project: Project | None
    # ─────────────────────────────────────────

    # [STEP 1] Charger par clé primaire → project chargé ou None
    project = await db.get(Project, project_id)

    # [STEP 2] Refuser l'absence → la sortie est garantie non nulle
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Project {project_id} not found")
    return project


# [RAG]
# signature: list_projects(db: AsyncSession, limit: int, offset: int) -> Sequence[Project]
# tier: LEAF
# weight: 1
# reads: projects
# mutates: none
# calls: none
# called_by: projects.router.list_projects
# [/RAG]
async def list_projects(db: AsyncSession, limit: int, offset: int) -> Sequence[Project]:
    """Liste les projets par page.

    Règles métier :
    - tri par id croissant : pagination stable et déterministe (D9) ;
    - bornes (1 ≤ limit ≤ 100, offset ≥ 0) validées en amont par le
      routeur — une liste vide est une réponse valide, pas une erreur.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    projects: Sequence[Project]
    # ─────────────────────────────────────────

    # [STEP 1] Charger la page demandée → tri par id, bornes appliquées
    projects = (
        await db.scalars(select(Project).order_by(Project.id).limit(limit).offset(offset))
    ).all()
    return projects


# [RAG]
# signature: update_project(db: AsyncSession, data: ProjectUpdate, project_id: int) -> Project
# tier: LEAF
# weight: 2
# reads: projects
# mutates: projects
# calls: projects.services.get_project
# called_by: projects.router.update_project
# [/RAG]
async def update_project(db: AsyncSession, data: ProjectUpdate, project_id: int) -> Project:
    """Modifie partiellement un projet.

    Règles métier :
    - sémantique ``exclude_unset`` : seuls les champs présents dans le
      corps changent — l'organisation n'est jamais modifiable (Phase 2) ;
    - un nouveau nom est soumis à la même unicité **dans l'organisation**
      que la création → 409 (D14) ;
    - id inconnu → 404.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    existing: Project | None
    field: str
    project: Project
    update_data: dict[str, Any]
    value: Any
    # ─────────────────────────────────────────

    # [STEP 1] Charger le projet cible → 404 si absent
    project = await get_project(db, project_id)

    # [STEP 2] Extraire les champs réellement fournis → PATCH partiel fidèle
    update_data = data.model_dump(exclude_unset=True)

    # [STEP 3] Vérifier l'unicité d'un nouveau nom dans l'organisation → aucun doublon local
    if "name" in update_data and update_data["name"] != project.name:
        existing = await db.scalar(
            select(Project).where(
                Project.organization_id == project.organization_id,
                Project.name == update_data["name"],
            )
        )
        if existing is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Project name already taken in this organization"
            )

    # [STEP 4] Appliquer les champs et persister → horodatage de modification rafraîchi
    for field, value in update_data.items():
        setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    return project
