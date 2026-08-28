# [FILE] — tests/unit/test_rag_probe.py
"""Tests unitaires du chunker de la sonde RAG (T077) — sans embedding.

Vérifient sur le mini-corpus annoté les règles de découpage du protocole
(jalon13-constat.md) : un chunk = un bloc [RAG] + sa fonction, un bloc
[MODEL]/[SCHEMA] seul, boilerplate d'imports exclu via [CODE_START]
(FR-016), et l'inventaire exact de l'échantillon réel figé.
"""

# ─── IMPORTS ───
from pathlib import Path

from scripts import generate_structural_metadata, generate_topology_headers, rag_probe
from tests.unit.corpus_fixtures import build_fixture_corpus

# ──────────────

# [CODE_START]


def test_code_chunks_exclude_imports_and_cover_functions(tmp_path: Path) -> None:
    """Chaque fonction annotée devient un chunk ; les imports n'y figurent pas."""
    # ─── VARIABLE DECLARATION ZONE ───
    app_dir: Path
    chunks: list[rag_probe.Chunk]
    lines: list[str]
    # ─────────────────────────────────

    # [STEP 1] Annoter la fixture puis chunker le noyau → un chunk par fonction
    app_dir = build_fixture_corpus(tmp_path)
    generate_topology_headers.annotate_corpus(app_dir)
    lines = (app_dir / "core/database.py").read_text(encoding="utf-8").splitlines()
    chunks = rag_probe._chunk_code("core.database", lines)

    # [STEP 2] Vérifier bornes et exclusions → en-tête inclus, boilerplate exclu
    assert [chunk.identifier for chunk in chunks] == [
        "core.database.get_db [RAG]",
        "core.database.helper_shared [RAG]",
    ]
    for chunk in chunks:
        assert chunk.text.startswith("# [RAG]")
        assert '"""Noyau DB de fixture."""' not in chunk.text


def test_model_file_yields_single_metadata_chunk(tmp_path: Path) -> None:
    """Un fichier de modèles donne son bloc [MODEL] seul — aucun chunk de code."""
    # ─── VARIABLE DECLARATION ZONE ───
    app_dir: Path
    lines: list[str]
    metadata: list[rag_probe.Chunk]
    # ─────────────────────────────────

    # [STEP 1] Générer la structure puis chunker users/models.py → bloc seul
    app_dir = build_fixture_corpus(tmp_path)
    generate_structural_metadata.annotate_structure(app_dir, tmp_path / "TOPOLOGY.yaml")
    lines = (app_dir / "domains/users/models.py").read_text(encoding="utf-8").splitlines()
    metadata = rag_probe._chunk_metadata("users.models", lines)

    # [STEP 2] Vérifier identifiant et contenu → signal d'arêtes embarqué
    assert [chunk.identifier for chunk in metadata] == ["users.models.User [MODEL]"]
    assert "# referenced_by:" in metadata[0].text
    assert rag_probe._chunk_code("users.models", lines) == []


def test_router_chunk_carries_depends(tmp_path: Path) -> None:
    """Le chunk d'un endpoint embarque décorateur et ``Depends(get_db)``."""
    # ─── VARIABLE DECLARATION ZONE ───
    app_dir: Path
    chunks: list[rag_probe.Chunk]
    lines: list[str]
    # ─────────────────────────────────

    # [STEP 1] Annoter puis chunker le routeur → l'arête Depends voyage avec le chunk
    app_dir = build_fixture_corpus(tmp_path)
    generate_topology_headers.annotate_corpus(app_dir)
    lines = (app_dir / "domains/users/router.py").read_text(encoding="utf-8").splitlines()
    chunks = rag_probe._chunk_code("users.router", lines)
    assert len(chunks) == 1
    assert '@router.post("")' in chunks[0].text
    assert "Depends(get_db)" in chunks[0].text


def test_sample_inventory_matches_frozen_protocol() -> None:
    """L'échantillon réel figé produit exactement l'inventaire attendu (19 chunks)."""
    # ─── VARIABLE DECLARATION ZONE ───
    chunks: list[rag_probe.Chunk]
    identifiers: list[str]
    # ─────────────────────────────────

    # [STEP 1] Chunker l'échantillon du dépôt → comptage et attendus du protocole
    chunks = rag_probe.collect_chunks(Path("."))
    identifiers = [chunk.identifier for chunk in chunks]
    assert len(chunks) == 19
    assert "users.services.delete_user [RAG]" in identifiers
    assert "users.models.User [MODEL]" in identifiers
    assert "core.database.get_db [RAG]" in identifiers
    assert all(c.text.startswith(("# [RAG]", "# [MODEL]", "# [SCHEMA]")) for c in chunks)
