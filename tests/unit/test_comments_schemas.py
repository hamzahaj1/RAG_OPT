# [FILE] — tests/unit/test_comments_schemas.py
"""Tests unitaires des schémas du domaine comments — aucun accès DB.

Vérifient le contrat de validation Pydantic : tâche, auteur et contenu
obligatoires à la création (aucun défaut implicite), et le PATCH minimal
du domaine — ``CommentUpdate`` vide valide, seul ``content`` modifiable.
"""

# ─── IMPORTS ───
import pytest
from pydantic import ValidationError

from app.domains.comments.schemas import CommentCreate, CommentUpdate

# ──────────────

# [CODE_START]

VALID_PAYLOAD: dict[str, str | int] = {
    "author_id": 1,
    "content": "Chunk index verified.",
    "task_id": 1,
}


def test_comment_create_accepts_valid_payload() -> None:
    """Un payload complet et conforme produit un schéma fidèle au contrat."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    schema: CommentCreate
    # ─────────────────────────────────────────

    # [STEP 1] Valider le payload de référence → tous les champs typés et normalisés
    schema = CommentCreate.model_validate(VALID_PAYLOAD)
    assert schema.author_id == 1
    assert schema.content == "Chunk index verified."
    assert schema.task_id == 1


def test_comment_create_rejects_missing_author_id() -> None:
    """L'auteur est obligatoire à la création — jamais implicite."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    payload: dict[str, str | int]
    # ─────────────────────────────────────────

    # [STEP 1] Soumettre un payload sans author_id → validation refusée
    payload = {key: value for key, value in VALID_PAYLOAD.items() if key != "author_id"}
    with pytest.raises(ValidationError):
        CommentCreate.model_validate(payload)


def test_comment_create_rejects_missing_content() -> None:
    """Le contenu est obligatoire à la création — aucun défaut, jamais NULL."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    payload: dict[str, str | int]
    # ─────────────────────────────────────────

    # [STEP 1] Soumettre un payload sans content → validation refusée
    payload = {key: value for key, value in VALID_PAYLOAD.items() if key != "content"}
    with pytest.raises(ValidationError):
        CommentCreate.model_validate(payload)


def test_comment_create_rejects_missing_task_id() -> None:
    """La tâche est obligatoire à la création — jamais implicite."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    payload: dict[str, str | int]
    # ─────────────────────────────────────────

    # [STEP 1] Soumettre un payload sans task_id → validation refusée
    payload = {key: value for key, value in VALID_PAYLOAD.items() if key != "task_id"}
    with pytest.raises(ValidationError):
        CommentCreate.model_validate(payload)


def test_comment_update_accepts_empty_payload() -> None:
    """``CommentUpdate`` vide est valide : un PATCH sans champ ne change rien."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    schema: CommentUpdate
    # ─────────────────────────────────────────

    # [STEP 1] Valider le corps vide → tous les champs restent non renseignés
    schema = CommentUpdate.model_validate({})
    assert schema.model_dump(exclude_unset=True) == {}


def test_comment_update_rejects_immutable_parents() -> None:
    """``task_id`` et ``author_id`` ne font pas partie du contrat de PATCH.

    C'est la garantie structurelle d'immutabilité des parents : les champs
    étrangers au schéma sont ignorés par validation — seul ``content``
    traverse ``model_dump(exclude_unset=True)``.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    schema: CommentUpdate
    # ─────────────────────────────────────────

    # [STEP 1] Valider un corps portant les parents → seuls les champs du contrat restent
    schema = CommentUpdate.model_validate({"author_id": 7, "content": "Edited.", "task_id": 9})
    assert schema.model_dump(exclude_unset=True) == {"content": "Edited."}
