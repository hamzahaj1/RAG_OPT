# [FILE] — tests/unit/test_projects_schemas.py
"""Tests unitaires des schémas du domaine projects — aucun accès DB.

Vérifient le contrat de validation Pydantic : présence obligatoire de
l'organisation à la création, défaut chaîne vide de la description,
longueur maximale du nom alignée sur la colonne, et PATCH vide valide
(sémantique ``exclude_unset``).
"""

# ─── IMPORTS ───
import pytest
from pydantic import ValidationError

from app.domains.projects.schemas import ProjectCreate, ProjectUpdate

# ──────────────

# [CODE_START]

VALID_PAYLOAD: dict[str, str | int] = {
    "description": "Pipeline RAG",
    "name": "Alpha Scope",
    "organization_id": 1,
}


def test_project_create_accepts_valid_payload() -> None:
    """Un payload complet et conforme produit un schéma fidèle au contrat."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    schema: ProjectCreate
    # ─────────────────────────────────────────

    # [STEP 1] Valider le payload de référence → tous les champs typés et normalisés
    schema = ProjectCreate.model_validate(VALID_PAYLOAD)
    assert schema.description == "Pipeline RAG"
    assert schema.name == "Alpha Scope"
    assert schema.organization_id == 1


def test_project_create_applies_description_default() -> None:
    """``description`` absente vaut chaîne vide — même défaut que la colonne (jamais NULL)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    schema: ProjectCreate
    # ─────────────────────────────────────────

    # [STEP 1] Valider un payload sans description → défaut chaîne vide appliqué
    schema = ProjectCreate.model_validate({"name": "Alpha Scope", "organization_id": 1})
    assert schema.description == ""


def test_project_create_rejects_missing_organization_id() -> None:
    """L'organisation est obligatoire à la création — jamais implicite."""
    # [STEP 1] Soumettre un payload sans organization_id → validation refusée
    with pytest.raises(ValidationError):
        ProjectCreate.model_validate({"description": "", "name": "Alpha Scope"})


def test_project_create_rejects_name_longer_than_max() -> None:
    """La longueur du nom est bornée à 100 (colonne VARCHAR(100))."""
    # [STEP 1] Soumettre un nom au-delà de la borne → validation refusée
    with pytest.raises(ValidationError):
        ProjectCreate.model_validate({**VALID_PAYLOAD, "name": "a" * 101})


def test_project_update_accepts_empty_payload() -> None:
    """``ProjectUpdate`` vide est valide : un PATCH sans champ ne change rien."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    schema: ProjectUpdate
    # ─────────────────────────────────────────

    # [STEP 1] Valider le corps vide → tous les champs restent non renseignés
    schema = ProjectUpdate.model_validate({})
    assert schema.model_dump(exclude_unset=True) == {}


def test_project_update_excludes_organization_id() -> None:
    """L'organisation n'est pas modifiable en Phase 2 — absente du schéma Update."""
    # [STEP 1] Inspecter les champs déclarés de ProjectUpdate → organization_id absent
    assert "organization_id" not in ProjectUpdate.model_fields
