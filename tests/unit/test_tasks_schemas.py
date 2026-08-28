# [FILE] — tests/unit/test_tasks_schemas.py
"""Tests unitaires des schémas du domaine tasks — aucun accès DB.

Vérifient le contrat de validation Pydantic : ensembles fermés status et
priority, assigné optionnel à la création, défaut chaîne vide de la
description, longueur maximale du titre, et la distinction structurante
du PATCH : champ absent ≠ ``null`` explicite (sémantique ``exclude_unset``).
"""

# ─── IMPORTS ───
import pytest
from pydantic import ValidationError

from app.domains.tasks.models import TaskPriority, TaskStatus
from app.domains.tasks.schemas import TaskCreate, TaskUpdate

# ──────────────

# [CODE_START]

VALID_PAYLOAD: dict[str, str | int] = {
    "description": "Indexer le corpus",
    "priority": "high",
    "project_id": 1,
    "status": "todo",
    "title": "Vectoriser les services",
}


def test_task_create_accepts_valid_payload() -> None:
    """Un payload complet et conforme produit un schéma fidèle au contrat."""
    # ─── VARIABLE DECLARATION ZONE ───
    schema: TaskCreate
    # ─────────────────────────────────

    # [STEP 1] Valider le payload de référence → tous les champs typés et normalisés
    schema = TaskCreate.model_validate(VALID_PAYLOAD)
    assert schema.description == "Indexer le corpus"
    assert schema.priority is TaskPriority.HIGH
    assert schema.project_id == 1
    assert schema.status is TaskStatus.TODO
    assert schema.title == "Vectoriser les services"


def test_task_create_allows_missing_assignee() -> None:
    """L'assigné est optionnel à la création : absent, la tâche naît non assignée."""
    # ─── VARIABLE DECLARATION ZONE ───
    schema: TaskCreate
    # ─────────────────────────────────

    # [STEP 1] Valider le payload sans assignee_id → défaut None appliqué
    schema = TaskCreate.model_validate(VALID_PAYLOAD)
    assert schema.assignee_id is None


def test_task_create_applies_description_default() -> None:
    """``description`` absente vaut chaîne vide — même défaut que la colonne (jamais NULL)."""
    # ─── VARIABLE DECLARATION ZONE ───
    payload: dict[str, str | int]
    schema: TaskCreate
    # ─────────────────────────────────

    # [STEP 1] Valider un payload sans description → défaut chaîne vide appliqué
    payload = {key: value for key, value in VALID_PAYLOAD.items() if key != "description"}
    schema = TaskCreate.model_validate(payload)
    assert schema.description == ""


def test_task_create_rejects_missing_project_id() -> None:
    """Le projet est obligatoire à la création — jamais implicite."""
    # ─── VARIABLE DECLARATION ZONE ───
    payload: dict[str, str | int]
    # ─────────────────────────────────

    # [STEP 1] Soumettre un payload sans project_id → validation refusée
    payload = {key: value for key, value in VALID_PAYLOAD.items() if key != "project_id"}
    with pytest.raises(ValidationError):
        TaskCreate.model_validate(payload)


def test_task_create_rejects_priority_outside_enum() -> None:
    """Une priorité hors de l'ensemble fermé ``TaskPriority`` est refusée (D1)."""
    # [STEP 1] Soumettre une priorité inconnue → validation refusée
    with pytest.raises(ValidationError):
        TaskCreate.model_validate({**VALID_PAYLOAD, "priority": "urgent"})


def test_task_create_rejects_status_outside_enum() -> None:
    """Un statut hors de l'ensemble fermé ``TaskStatus`` est refusé (D1)."""
    # [STEP 1] Soumettre un statut inconnu → validation refusée
    with pytest.raises(ValidationError):
        TaskCreate.model_validate({**VALID_PAYLOAD, "status": "archived"})


def test_task_create_rejects_title_longer_than_max() -> None:
    """La longueur du titre est bornée à 200 (colonne VARCHAR(200))."""
    # [STEP 1] Soumettre un titre au-delà de la borne → validation refusée
    with pytest.raises(ValidationError):
        TaskCreate.model_validate({**VALID_PAYLOAD, "title": "a" * 201})


def test_task_update_accepts_empty_payload() -> None:
    """``TaskUpdate`` vide est valide : un PATCH sans champ ne change rien."""
    # ─── VARIABLE DECLARATION ZONE ───
    schema: TaskUpdate
    # ─────────────────────────────────

    # [STEP 1] Valider le corps vide → tous les champs restent non renseignés
    schema = TaskUpdate.model_validate({})
    assert schema.model_dump(exclude_unset=True) == {}


def test_task_update_distinguishes_absent_field_from_explicit_null() -> None:
    """Champ absent ≠ ``null`` explicite : ``exclude_unset`` conserve le null fourni.

    C'est le contrat de désassignation : ``{"assignee_id": null}`` doit
    traverser ``model_dump(exclude_unset=True)`` pour produire le SET NULL
    applicatif, tandis qu'un corps sans le champ ne touche pas l'assignation.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    with_explicit_null: TaskUpdate
    without_field: TaskUpdate
    # ─────────────────────────────────

    # [STEP 1] Valider un corps sans le champ → assignee_id exclu du dump partiel
    without_field = TaskUpdate.model_validate({"title": "Retitrée"})
    assert "assignee_id" not in without_field.model_dump(exclude_unset=True)

    # [STEP 2] Valider un null explicite → assignee_id conservé à None dans le dump
    with_explicit_null = TaskUpdate.model_validate({"assignee_id": None})
    assert with_explicit_null.model_dump(exclude_unset=True) == {"assignee_id": None}
