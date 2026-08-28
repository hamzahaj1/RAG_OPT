# [FILE] — tests/unit/test_users_schemas.py
"""Tests unitaires des schémas du domaine users — aucun accès DB.

Vérifient le contrat de validation Pydantic : formats, ensembles fermés,
longueurs maximales alignées sur les colonnes, et absence de tout champ
mot de passe dans les réponses (FR-009).
"""

# ─── IMPORTS ───
import pytest
from pydantic import ValidationError

from app.domains.users.models import UserRole
from app.domains.users.schemas import UserCreate, UserRead, UserUpdate

# ──────────────

# [CODE_START]

VALID_PAYLOAD: dict[str, str] = {
    "email": "alice@example.com",
    "full_name": "Alice",
    "password": "s3cret-pw",
    "role": "admin",
}


def test_user_create_accepts_valid_payload() -> None:
    """Un payload complet et conforme produit un schéma fidèle au contrat."""
    # ─── VARIABLE DECLARATION ZONE ───
    schema: UserCreate
    # ─────────────────────────────────

    # [STEP 1] Valider le payload de référence → tous les champs typés et normalisés
    schema = UserCreate.model_validate(VALID_PAYLOAD)
    assert schema.email == "alice@example.com"
    assert schema.full_name == "Alice"
    assert schema.password == "s3cret-pw"
    assert schema.role is UserRole.ADMIN


def test_user_create_rejects_email_longer_than_max() -> None:
    """La longueur de l'email est bornée à 255 (colonne VARCHAR(255))."""
    # [STEP 1] Soumettre un email au-delà de la borne → validation refusée
    with pytest.raises(ValidationError):
        UserCreate.model_validate({**VALID_PAYLOAD, "email": f"{'a' * 250}@example.com"})


def test_user_create_rejects_full_name_longer_than_max() -> None:
    """La longueur du nom est bornée à 100 (colonne VARCHAR(100))."""
    # [STEP 1] Soumettre un nom au-delà de la borne → validation refusée
    with pytest.raises(ValidationError):
        UserCreate.model_validate({**VALID_PAYLOAD, "full_name": "a" * 101})


def test_user_create_rejects_invalid_email() -> None:
    """Un email sans forme valide est refusé par ``EmailStr``."""
    # [STEP 1] Soumettre un email non conforme → validation refusée
    with pytest.raises(ValidationError):
        UserCreate.model_validate({**VALID_PAYLOAD, "email": "not-an-email"})


def test_user_create_rejects_role_outside_enum() -> None:
    """Un rôle hors de l'ensemble fermé ``UserRole`` est refusé (FR-008)."""
    # [STEP 1] Soumettre un rôle inconnu → validation refusée
    with pytest.raises(ValidationError):
        UserCreate.model_validate({**VALID_PAYLOAD, "role": "owner"})


def test_user_create_rejects_short_password() -> None:
    """Un mot de passe de moins de 8 caractères est refusé."""
    # [STEP 1] Soumettre un mot de passe trop court → validation refusée
    with pytest.raises(ValidationError):
        UserCreate.model_validate({**VALID_PAYLOAD, "password": "short"})


def test_user_read_excludes_password_fields() -> None:
    """Aucun champ mot de passe, en clair ou haché, dans les réponses (FR-009)."""
    # [STEP 1] Inspecter les champs déclarés de UserRead → aucun champ sensible
    assert "password" not in UserRead.model_fields
    assert "hashed_password" not in UserRead.model_fields


def test_user_update_accepts_empty_payload() -> None:
    """``UserUpdate`` vide est valide : un PATCH sans champ ne change rien."""
    # ─── VARIABLE DECLARATION ZONE ───
    schema: UserUpdate
    # ─────────────────────────────────

    # [STEP 1] Valider le corps vide → tous les champs restent non renseignés
    schema = UserUpdate.model_validate({})
    assert schema.model_dump(exclude_unset=True) == {}
