# [FILE] — app/domains/organizations/services.py
"""Logique métier du domaine organizations.

Porte toutes les règles du domaine — les routeurs restent des wrappers
minces : existence du propriétaire vérifiée par SELECT avant toute
écriture (404, première couche de D2 — la FK ``RESTRICT`` est le
backstop), unicité du nom (409), 404 nommant l'entité et l'id. Une
écriture par requête HTTP : ``commit`` puis ``refresh`` ici, jamais dans
les routeurs.
"""

# ─── IMPORTS ───
from collections.abc import Sequence
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.organizations.models import Organization
from app.domains.organizations.schemas import OrganizationCreate, OrganizationUpdate
from app.domains.projects.models import Project
from app.domains.users.models import User

# ──────────────

# [CODE_START]


# [RAG]
# signature: create_organization(db: AsyncSession, data: OrganizationCreate) -> Organization
# tier: CORE
# weight: 2
# reads: organizations, users
# mutates: organizations
# calls: none
# called_by: organizations.router.create_organization, scripts.seed._ensure_organization
# [/RAG]
async def create_organization(db: AsyncSession, data: OrganizationCreate) -> Organization:
    """Crée une organisation.

    Règles métier :
    - le propriétaire doit exister : SELECT sur ``users`` avant toute
      écriture → 404 « User {id} not found » (FR-011, D2) ;
    - le nom est unique sur toute la plateforme : un doublon est refusé
      en 409 avant toute écriture (FR-012).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    existing: Organization | None
    organization: Organization
    owner: User | None
    # ─────────────────────────────────────────

    # [STEP 1] Vérifier l'existence du propriétaire → aucune FK orpheline ne sera écrite
    owner = await db.get(User, data.owner_id)
    if owner is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {data.owner_id} not found")

    # [STEP 2] Vérifier la disponibilité du nom → aucun doublon ne sera écrit
    existing = await db.scalar(select(Organization).where(Organization.name == data.name))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Organization name already taken")

    # [STEP 3] Persister et rafraîchir → id et horodatages serveur résolus
    organization = Organization(name=data.name, owner_id=data.owner_id)
    db.add(organization)
    await db.commit()
    await db.refresh(organization)
    return organization


# [RAG]
# signature: delete_organization(db: AsyncSession, organization_id: int) -> None
# tier: LEAF
# weight: 2
# reads: projects
# mutates: organizations
# calls: organizations.services.get_organization
# called_by: organizations.router.delete_organization
# [/RAG]
async def delete_organization(db: AsyncSession, organization_id: int) -> None:
    """Supprime une organisation.

    Règles métier :
    - id inconnu → 404, aucune écriture ;
    - organisation contenant au moins un projet → 409 avant toute
      écriture (SELECT applicatif, la FK ``RESTRICT`` reste le
      backstop — D2) : la suppression est bloquée par les projets,
      jamais propagée vers eux.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    held: Project | None
    organization: Organization
    # ─────────────────────────────────────────

    # [STEP 1] Charger l'organisation cible → 404 si absente
    organization = await get_organization(db, organization_id)

    # [STEP 2] Refuser une organisation occupée → aucune FK orpheline possible
    held = await db.scalar(select(Project).where(Project.organization_id == organization_id))
    if held is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Organization {organization_id} still has projects"
        )

    # [STEP 3] Supprimer et valider → la ligne n'existe plus
    await db.delete(organization)
    await db.commit()


# [RAG]
# signature: get_organization(db: AsyncSession, organization_id: int) -> Organization
# tier: CORE
# weight: 3
# reads: organizations
# mutates: none
# calls: none
# called_by: organizations.router.get_organization, organizations.services.delete_organization,
#   organizations.services.update_organization
# [/RAG]
async def get_organization(db: AsyncSession, organization_id: int) -> Organization:
    """Consulte une organisation par identifiant.

    Règles métier :
    - id inconnu → 404 nommant l'entité et l'id (« Organization 42 not
      found »), format d'erreur commun aux cinq domaines (FR-003).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    organization: Organization | None
    # ─────────────────────────────────────────

    # [STEP 1] Charger par clé primaire → organization chargée ou None
    organization = await db.get(Organization, organization_id)

    # [STEP 2] Refuser l'absence → la sortie est garantie non nulle
    if organization is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Organization {organization_id} not found")
    return organization


# [RAG]
# signature: list_organizations(db: AsyncSession, limit: int, offset: int) -> Sequence[Organization]
# tier: LEAF
# weight: 1
# reads: organizations
# mutates: none
# calls: none
# called_by: organizations.router.list_organizations
# [/RAG]
async def list_organizations(db: AsyncSession, limit: int, offset: int) -> Sequence[Organization]:
    """Liste les organisations par page.

    Règles métier :
    - tri par id croissant : pagination stable et déterministe (D9) ;
    - bornes (1 ≤ limit ≤ 100, offset ≥ 0) validées en amont par le
      routeur — une liste vide est une réponse valide, pas une erreur.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    organizations: Sequence[Organization]
    # ─────────────────────────────────────────

    # [STEP 1] Charger la page demandée → tri par id, bornes appliquées
    organizations = (
        await db.scalars(select(Organization).order_by(Organization.id).limit(limit).offset(offset))
    ).all()
    return organizations


# [RAG]
# signature: update_organization(db: AsyncSession, data: OrganizationUpdate,
#   organization_id: int) -> Organization
# tier: LEAF
# weight: 2
# reads: organizations
# mutates: organizations
# calls: organizations.services.get_organization
# called_by: organizations.router.update_organization
# [/RAG]
async def update_organization(
    db: AsyncSession, data: OrganizationUpdate, organization_id: int
) -> Organization:
    """Modifie partiellement une organisation.

    Règles métier :
    - sémantique ``exclude_unset`` : seuls les champs présents dans le
      corps changent — le propriétaire n'est jamais modifiable (Phase 2) ;
    - un nouveau nom est soumis à la même unicité que la création → 409 ;
    - id inconnu → 404.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    existing: Organization | None
    field: str
    organization: Organization
    update_data: dict[str, Any]
    value: Any
    # ─────────────────────────────────────────

    # [STEP 1] Charger l'organisation cible → 404 si absente
    organization = await get_organization(db, organization_id)

    # [STEP 2] Extraire les champs réellement fournis → PATCH partiel fidèle
    update_data = data.model_dump(exclude_unset=True)

    # [STEP 3] Vérifier l'unicité d'un nouveau nom → aucun doublon ne sera écrit
    if "name" in update_data and update_data["name"] != organization.name:
        existing = await db.scalar(
            select(Organization).where(Organization.name == update_data["name"])
        )
        if existing is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Organization name already taken")

    # [STEP 4] Appliquer les champs et persister → horodatage de modification rafraîchi
    for field, value in update_data.items():
        setattr(organization, field, value)
    await db.commit()
    await db.refresh(organization)
    return organization
