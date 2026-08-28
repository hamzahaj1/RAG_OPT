# [FILE] — tests/unit/test_organizations_schemas.py
"""Tests unitaires des schémas du domaine organizations — aucun accès DB.

Vérifient le contrat de validation Pydantic : présence obligatoire du
propriétaire à la création, longueur maximale du nom alignée sur la
colonne, et PATCH vide valide (sémantique ``exclude_unset``).
"""

# ─── IMPORTS ───
import pytest
from pydantic import ValidationError

from app.domains.organizations.schemas import OrganizationCreate, OrganizationUpdate

# ──────────────

# [CODE_START]

VALID_PAYLOAD: dict[str, str | int] = {
    "name": "Acme Corp",
    "owner_id": 1,
}


def test_organization_create_accepts_valid_payload() -> None:
    """Un payload complet et conforme produit un schéma fidèle au contrat."""
    # ─── VARIABLE DECLARATION ZONE ───
    schema: OrganizationCreate
    # ─────────────────────────────────

    # [STEP 1] Valider le payload de référence → tous les champs typés et normalisés
    schema = OrganizationCreate.model_validate(VALID_PAYLOAD)
    assert schema.name == "Acme Corp"
    assert schema.owner_id == 1


def test_organization_create_rejects_missing_owner_id() -> None:
    """Le propriétaire est obligatoire à la création (FR-011) — jamais implicite."""
    # [STEP 1] Soumettre un payload sans owner_id → validation refusée
    with pytest.raises(ValidationError):
        OrganizationCreate.model_validate({"name": "Acme Corp"})


def test_organization_create_rejects_name_longer_than_max() -> None:
    """La longueur du nom est bornée à 100 (colonne VARCHAR(100))."""
    # [STEP 1] Soumettre un nom au-delà de la borne → validation refusée
    with pytest.raises(ValidationError):
        OrganizationCreate.model_validate({**VALID_PAYLOAD, "name": "a" * 101})


def test_organization_update_accepts_empty_payload() -> None:
    """``OrganizationUpdate`` vide est valide : un PATCH sans champ ne change rien."""
    # ─── VARIABLE DECLARATION ZONE ───
    schema: OrganizationUpdate
    # ─────────────────────────────────

    # [STEP 1] Valider le corps vide → tous les champs restent non renseignés
    schema = OrganizationUpdate.model_validate({})
    assert schema.model_dump(exclude_unset=True) == {}


def test_organization_update_excludes_owner_id() -> None:
    """Le propriétaire n'est pas modifiable en Phase 2 — absent du schéma Update."""
    # [STEP 1] Inspecter les champs déclarés de OrganizationUpdate → owner_id absent
    assert "owner_id" not in OrganizationUpdate.model_fields
