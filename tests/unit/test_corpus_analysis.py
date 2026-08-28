# [FILE] — tests/unit/test_corpus_analysis.py
"""Tests unitaires du module d'analyse partagé (T057) — aucun accès DB.

Vérifient sur le mini-corpus de fixture les règles figées du graphe
(R1–R2) : résolution des alias de modules, arêtes ``Depends``, échelle
weight/tier, reads/mutates, et l'échec explicite sur symbole non résolu
(FR-007) — jamais un en-tête silencieusement incomplet.
"""

# ─── IMPORTS ───
from pathlib import Path

import pytest

from scripts import corpus_analysis
from tests.unit.corpus_fixtures import build_fixture_corpus

# ──────────────

# [CODE_START]


def test_alias_module_call_is_resolved_to_real_target(tmp_path: Path) -> None:
    """``import ... as s ; s.f()`` crée l'arête vers la cible réelle (R2.2)."""
    # ─── VARIABLE DECLARATION ZONE ───
    graph: corpus_analysis.CorpusGraph
    # ─────────────────────────────────

    # [STEP 1] Analyser le mini-corpus → arête du seed aliasé vers le service
    graph = corpus_analysis.analyze_corpus(build_fixture_corpus(tmp_path))
    assert ("scripts.seed.run", "users.services.create_user") in graph.edges


def test_depends_creates_incoming_edge_to_get_db(tmp_path: Path) -> None:
    """``Depends(get_db)`` est une arête entrante vers ``get_db`` (R2.1)."""
    # ─── VARIABLE DECLARATION ZONE ───
    graph: corpus_analysis.CorpusGraph
    # ─────────────────────────────────

    # [STEP 1] Analyser le mini-corpus → l'endpoint apparaît en appelant de get_db
    graph = corpus_analysis.analyze_corpus(build_fixture_corpus(tmp_path))
    assert "users.router.create_user" in corpus_analysis.called_by_of(graph, "core.database.get_db")


def test_leaf_endpoint_and_core_service_tiers(tmp_path: Path) -> None:
    """Endpoint sans appel entrant → LEAF ; service référencé par le seed → CORE."""
    # ─── VARIABLE DECLARATION ZONE ───
    graph: corpus_analysis.CorpusGraph
    # ─────────────────────────────────

    # [STEP 1] Analyser le mini-corpus → échelle fermée respectée (R1)
    graph = corpus_analysis.analyze_corpus(build_fixture_corpus(tmp_path))
    assert corpus_analysis.tier_of(graph, "users.router.create_user") == "LEAF"
    assert corpus_analysis.tier_of(graph, "users.services.create_user") == "CORE"


def test_reads_exclude_constructor_and_mutates_follow_db_add(tmp_path: Path) -> None:
    """``select(User)`` est une lecture, ``db.add`` une mutation de table."""
    # ─── VARIABLE DECLARATION ZONE ───
    graph: corpus_analysis.CorpusGraph
    # ─────────────────────────────────

    # [STEP 1] Analyser le mini-corpus → empreintes reads/mutates exactes
    graph = corpus_analysis.analyze_corpus(build_fixture_corpus(tmp_path))
    assert graph.reads["users.services.create_user"] == {"users"}
    assert graph.mutates["users.services.create_user"] == {"users"}


def test_settings_is_read_entity_and_critical_core(tmp_path: Path) -> None:
    """``settings`` est une entité lue et un membre nommé du cœur critique (R1)."""
    # ─── VARIABLE DECLARATION ZONE ───
    graph: corpus_analysis.CorpusGraph
    # ─────────────────────────────────

    # [STEP 1] Analyser le mini-corpus → lecture tracée, tier figé
    graph = corpus_analysis.analyze_corpus(build_fixture_corpus(tmp_path))
    assert "settings" in graph.reads["main.create_app"]
    assert "main.create_app" in graph.settings_readers
    assert corpus_analysis.tier_of(graph, corpus_analysis.SETTINGS_QUALIFIED) == "CRITICAL_CORE"


def test_three_calling_domains_promote_critical_core(tmp_path: Path) -> None:
    """Une fonction référencée par 3 domaines distincts monte en CRITICAL_CORE (R1)."""
    # ─── VARIABLE DECLARATION ZONE ───
    callers: list[str]
    graph: corpus_analysis.CorpusGraph
    # ─────────────────────────────────

    # [STEP 1] Analyser le mini-corpus → trois domaines appellent helper_shared
    graph = corpus_analysis.analyze_corpus(build_fixture_corpus(tmp_path))
    callers = corpus_analysis.called_by_of(graph, "core.database.helper_shared")
    assert {caller.split(".")[0] for caller in callers} == {
        "organizations",
        "projects",
        "users",
    }
    assert corpus_analysis.tier_of(graph, "core.database.helper_shared") == "CRITICAL_CORE"


def test_unresolved_call_raises_named_error(tmp_path: Path) -> None:
    """Un appel vers un nom inconnu échoue en nommant fichier et symbole (FR-007)."""
    # ─── VARIABLE DECLARATION ZONE ───
    app_dir: Path
    # ─────────────────────────────────

    # [STEP 1] Poser un corpus minimal fautif → appel d'un nom jamais défini
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "main.py").write_text(
        '"""Fautif."""\n\n\ndef boom():\n    """Appelle un fantôme."""\n'
        "    return ghost_function()\n",
        encoding="utf-8",
    )

    # [STEP 2] Analyser → échec explicite portant fichier et symbole
    with pytest.raises(corpus_analysis.UnresolvedSymbolError, match="ghost_function"):
        corpus_analysis.analyze_corpus(app_dir)


def test_unresolved_import_raises_named_error(tmp_path: Path) -> None:
    """Un from-import ``app.*`` vers un symbole absent échoue nommément (FR-007)."""
    # ─── VARIABLE DECLARATION ZONE ───
    app_dir: Path
    # ─────────────────────────────────

    # [STEP 1] Corrompre le mini-corpus → import d'un symbole inexistant du noyau
    app_dir = build_fixture_corpus(tmp_path)
    (app_dir / "main.py").write_text(
        '"""Fautif."""\n\nfrom app.core.database import missing_symbol\n',
        encoding="utf-8",
    )

    # [STEP 2] Analyser → échec explicite portant le symbole fautif
    with pytest.raises(corpus_analysis.UnresolvedSymbolError, match="missing_symbol"):
        corpus_analysis.analyze_corpus(app_dir)


def test_weight_counts_in_and_out_edges(tmp_path: Path) -> None:
    """``weight`` = arêtes entrantes + sortantes dans le graphe résolu (R1)."""
    # ─── VARIABLE DECLARATION ZONE ───
    graph: corpus_analysis.CorpusGraph
    # ─────────────────────────────────

    # [STEP 1] Analyser le mini-corpus → 2 entrantes (routeur, seed) + 1 sortante
    graph = corpus_analysis.analyze_corpus(build_fixture_corpus(tmp_path))
    assert corpus_analysis.weight_of(graph, "users.services.create_user") == 3
