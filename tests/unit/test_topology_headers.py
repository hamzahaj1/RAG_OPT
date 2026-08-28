# [FILE] — tests/unit/test_topology_headers.py
"""Tests unitaires du générateur d'en-têtes [RAG] (T059) — aucun accès DB.

Vérifient sur le mini-corpus de fixture le format et l'ancrage des blocs,
l'idempotence du remplacement délimité (FR-002), l'absence d'accumulation
sur bloc périmé, et l'intangibilité des fichiers hors périmètre
(``models.py``/``schemas.py``).
"""

# ─── IMPORTS ───
from pathlib import Path

from scripts import generate_topology_headers
from tests.unit.corpus_fixtures import build_fixture_corpus

# ──────────────

# [CODE_START]


def test_call_lists_capped_with_deterministic_synthesis() -> None:
    """Au-delà de 5 entrées, le champ d'appels devient une synthèse (plan, J10)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    rendered: list[str]
    values: list[str]
    # ─────────────────────────────────────────

    # [STEP 1] Soumettre 6 appelants sur 2 domaines → résumé déterministe attendu
    values = [
        "organizations.router.create_organization",
        "users.router.create_user",
        "users.router.delete_user",
        "users.router.get_user",
        "users.router.list_users",
        "users.router.update_user",
    ]
    rendered = generate_topology_headers._format_call_field("called_by", "inbound", values)
    assert rendered == [
        "# called_by: 6 inbound calls — 2 domains (organizations, users) — details: TOPOLOGY.yaml"
    ]

    # [STEP 2] Rester sous le plafond → liste inchangée, cas nominal préservé
    assert generate_topology_headers._format_call_field("calls", "outbound", values[:2]) == [
        "# calls: " + ", ".join(values[:2])
    ]


def test_double_run_leaves_files_identical(tmp_path: Path) -> None:
    """Deux exécutions successives sur corpus inchangé = diff vide (FR-002)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    app_dir: Path
    changed_second: list[str]
    snapshots: dict[Path, str]
    # ─────────────────────────────────────────

    # [STEP 1] Annoter une première fois → état de référence photographié
    app_dir = build_fixture_corpus(tmp_path)
    generate_topology_headers.annotate_corpus(app_dir)
    snapshots = {path: path.read_text(encoding="utf-8") for path in sorted(app_dir.rglob("*.py"))}

    # [STEP 2] Annoter une seconde fois → aucun fichier modifié, contenus identiques
    changed_second = generate_topology_headers.annotate_corpus(app_dir)
    assert changed_second == []
    for path, content in snapshots.items():
        assert path.read_text(encoding="utf-8") == content


def test_headers_inserted_with_expected_fields(tmp_path: Path) -> None:
    """Chaque fonction cible reçoit un bloc complet, ancré au-dessus du bloc décoré."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    app_dir: Path
    router_text: str
    services_text: str
    # ─────────────────────────────────────────

    # [STEP 1] Annoter le mini-corpus → blocs présents dans services et routeur
    app_dir = build_fixture_corpus(tmp_path)
    generate_topology_headers.annotate_corpus(app_dir)
    services_text = (app_dir / "domains/users/services.py").read_text(encoding="utf-8")
    router_text = (app_dir / "domains/users/router.py").read_text(encoding="utf-8")

    # [STEP 2] Vérifier le contenu du bloc service → ordre amendé J10, valeurs exactes
    assert "# [RAG]\n# signature: create_user(db, data)\n# tier: CORE\n# weight: 3" in services_text
    assert "# weight: 3\n# reads: users\n# mutates: users\n# calls:" in services_text
    assert (
        "# called_by: scripts.seed.run, users.router.create_user\n# [/RAG]\nasync def create_user"
        in services_text
    )

    # [STEP 3] Vérifier l'ancrage routeur → bloc au-dessus du décorateur, arête Depends
    assert '# [/RAG]\n@router.post("")' in router_text
    assert "# calls: core.database.get_db, users.services.create_user" in router_text


def test_models_and_schemas_files_untouched(tmp_path: Path) -> None:
    """Les fichiers hors périmètre [RAG] ne sont jamais réécrits (CLAUDE.md §7)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    app_dir: Path
    models_before: str
    schemas_before: str
    # ─────────────────────────────────────────

    # [STEP 1] Photographier modèles et schémas → référence avant annotation
    app_dir = build_fixture_corpus(tmp_path)
    models_before = (app_dir / "domains/users/models.py").read_text(encoding="utf-8")
    schemas_before = (app_dir / "domains/users/schemas.py").read_text(encoding="utf-8")

    # [STEP 2] Annoter → contenus strictement inchangés hors périmètre
    generate_topology_headers.annotate_corpus(app_dir)
    assert (app_dir / "domains/users/models.py").read_text(encoding="utf-8") == models_before
    assert (app_dir / "domains/users/schemas.py").read_text(encoding="utf-8") == schemas_before


def test_stale_block_is_replaced_without_accumulation(tmp_path: Path) -> None:
    """Un bloc périmé est intégralement remplacé — jamais dupliqué (R3)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    app_dir: Path
    reference: str
    services_path: Path
    tampered: str
    # ─────────────────────────────────────────

    # [STEP 1] Annoter puis corrompre le bloc → poids falsifié dans le fichier
    app_dir = build_fixture_corpus(tmp_path)
    generate_topology_headers.annotate_corpus(app_dir)
    services_path = app_dir / "domains/users/services.py"
    reference = services_path.read_text(encoding="utf-8")
    tampered = reference.replace("# weight: 3", "# weight: 999")
    services_path.write_text(tampered, encoding="utf-8")

    # [STEP 2] Ré-annoter → bloc corrigé, aucun marqueur surnuméraire
    generate_topology_headers.annotate_corpus(app_dir)
    assert services_path.read_text(encoding="utf-8") == reference
    assert services_path.read_text(encoding="utf-8").count("# [RAG]") == reference.count("# [RAG]")
