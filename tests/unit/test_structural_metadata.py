# [FILE] — tests/unit/test_structural_metadata.py
"""Tests unitaires du générateur structurel (T066) — aucun accès DB.

Vérifient sur le mini-corpus de fixture le format et l'ancrage des blocs
[MODEL]/[SCHEMA], les politiques ``ondelete`` portées par ``fks`` et
``referenced_by`` (signal RAG de la suppression), l'idempotence du
remplacement délimité, et l'identité octet pour octet de
``TOPOLOGY.yaml`` entre deux générations (FR-012, SC-002).
"""

# ─── IMPORTS ───
from pathlib import Path

import pytest

from scripts import corpus_analysis, generate_structural_metadata
from tests.unit.corpus_fixtures import build_fixture_corpus

# ──────────────

# [CODE_START]


def test_double_generation_yields_identical_topology(tmp_path: Path) -> None:
    """Deux générations sur corpus inchangé = TOPOLOGY.yaml identique (SC-002)."""
    # ─── VARIABLE DECLARATION ZONE ───
    app_dir: Path
    changed_second: list[str]
    first_bytes: bytes
    topology_path: Path
    # ─────────────────────────────────

    # [STEP 1] Générer une première fois → référence octet pour octet
    app_dir = build_fixture_corpus(tmp_path)
    topology_path = tmp_path / "TOPOLOGY.yaml"
    generate_structural_metadata.annotate_structure(app_dir, topology_path)
    first_bytes = topology_path.read_bytes()

    # [STEP 2] Générer une seconde fois → aucun fichier modifié, identité stricte
    changed_second = generate_structural_metadata.annotate_structure(app_dir, topology_path)
    assert changed_second == []
    assert topology_path.read_bytes() == first_bytes


def test_missing_file_marker_fails_explicitly(tmp_path: Path) -> None:
    """Un fichier cible sans marqueur ``# [FILE]`` est un échec nommé, pas un silence."""
    # ─── VARIABLE DECLARATION ZONE ───
    app_dir: Path
    models_path: Path
    # ─────────────────────────────────

    # [STEP 1] Priver un modèle de son marqueur → ancrage impossible
    app_dir = build_fixture_corpus(tmp_path)
    models_path = app_dir / "domains/users/models.py"
    models_path.write_text(
        models_path.read_text(encoding="utf-8").split("\n", 1)[1], encoding="utf-8"
    )

    # [STEP 2] Générer → échec explicite nommant le fichier
    with pytest.raises(corpus_analysis.UnresolvedSymbolError, match="users/models.py"):
        generate_structural_metadata.annotate_structure(app_dir, tmp_path / "TOPOLOGY.yaml")


def test_model_blocks_carry_delete_policies(tmp_path: Path) -> None:
    """``fks`` et ``referenced_by`` portent les politiques ondelete par arête."""
    # ─── VARIABLE DECLARATION ZONE ───
    app_dir: Path
    comments_text: str
    tasks_text: str
    users_text: str
    # ─────────────────────────────────

    # [STEP 1] Générer la structure → blocs [MODEL] posés sur les trois modèles
    app_dir = build_fixture_corpus(tmp_path)
    generate_structural_metadata.annotate_structure(app_dir, tmp_path / "TOPOLOGY.yaml")
    comments_text = (app_dir / "domains/comments/models.py").read_text(encoding="utf-8")
    tasks_text = (app_dir / "domains/tasks/models.py").read_text(encoding="utf-8")
    users_text = (app_dir / "domains/users/models.py").read_text(encoding="utf-8")

    # [STEP 2] Vérifier les FK sortantes → politiques exactes, triées par colonne
    assert "# fks: author_id -> users.id [RESTRICT], task_id -> tasks.id [CASCADE]" in comments_text
    assert "# fks: assignee_id -> users.id [SET NULL]" in tasks_text

    # [STEP 3] Vérifier les arêtes entrantes → signal RAG de la suppression
    assert (
        "# referenced_by: comments.author_id -> RESTRICT, tasks.assignee_id -> SET NULL"
        in users_text
    )
    assert "# referenced_by: comments.task_id -> CASCADE" in tasks_text
    assert "# entity: User\n# table: users" in users_text

    # [STEP 4] Vérifier les synthèses anglaises générées → gabarit et gloses figés (J11, §4 ter)
    assert (
        "# synthesis: A User is referenced by comments.author_id (RESTRICT — blocked),"
        in users_text
    )
    assert "tasks.assignee_id (SET NULL — unassigned)." in users_text
    assert "# synthesis: A Comment is not referenced by any table." in comments_text
    assert "# synthesis: A Task is referenced by comments.task_id" in tasks_text


def test_schema_block_fields_and_anchor(tmp_path: Path) -> None:
    """Le bloc [SCHEMA] suit immédiatement ``# [FILE]`` avec ses trois champs."""
    # ─── VARIABLE DECLARATION ZONE ───
    app_dir: Path
    lines: list[str]
    # ─────────────────────────────────

    # [STEP 1] Générer la structure → bloc [SCHEMA] ancré sous le marqueur
    app_dir = build_fixture_corpus(tmp_path)
    generate_structural_metadata.annotate_structure(app_dir, tmp_path / "TOPOLOGY.yaml")
    lines = (app_dir / "domains/users/schemas.py").read_text(encoding="utf-8").splitlines()

    # [STEP 2] Vérifier ancrage et champs → synthèse en tête (J11), ordre fixe
    assert lines[0].startswith("# [FILE]")
    assert lines[1] == "# [SCHEMA]"
    assert lines[2] == (
        "# synthesis: The Pydantic schema of the users domain carries the contract"
        " of the User entity."
    )
    assert lines[3] == "# domain: users"
    assert lines[4] == "# schemas: UserCreate(BaseModel)"
    assert lines[5] == "# entity: User"
    assert lines[6] == "# [/SCHEMA]"


def test_stale_block_is_replaced_without_accumulation(tmp_path: Path) -> None:
    """Un bloc [MODEL] périmé est intégralement remplacé — jamais dupliqué (R3)."""
    # ─── VARIABLE DECLARATION ZONE ───
    app_dir: Path
    reference: str
    tasks_path: Path
    # ─────────────────────────────────

    # [STEP 1] Générer puis corrompre la politique → bloc périmé dans le fichier
    app_dir = build_fixture_corpus(tmp_path)
    generate_structural_metadata.annotate_structure(app_dir, tmp_path / "TOPOLOGY.yaml")
    tasks_path = app_dir / "domains/tasks/models.py"
    reference = tasks_path.read_text(encoding="utf-8")
    tasks_path.write_text(reference.replace("[SET NULL]", "[CASCADE]"), encoding="utf-8")

    # [STEP 2] Régénérer → bloc corrigé, aucun marqueur surnuméraire
    generate_structural_metadata.annotate_structure(app_dir, tmp_path / "TOPOLOGY.yaml")
    assert tasks_path.read_text(encoding="utf-8") == reference
    assert tasks_path.read_text(encoding="utf-8").count("# [MODEL]") == 1
