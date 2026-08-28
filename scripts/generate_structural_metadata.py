# [FILE] — scripts/generate_structural_metadata.py
"""Générateur des métadonnées structurelles — consommateur de l'analyse T056.

Insère les blocs ``# [MODEL]`` … ``# [/MODEL]`` sur les ``models.py`` et
``# [SCHEMA]`` … ``# [/SCHEMA]`` sur les ``schemas.py`` (ancrage :
immédiatement après la ligne ``# [FILE]``), puis produit ``TOPOLOGY.yaml``
à la racine — graphe d'appels complet du corpus en sérialisation
déterministe (R4) : ``safe_dump(sort_keys=True)``, listes pré-triées,
aucun horodatage, UTF-8, LF, newline final unique. Même mécanique de
remplacement délimité que les en-têtes [RAG] (R3) : deux exécutions
successives sur un code inchangé laissent l'arbre strictement identique.

Le champ ``referenced_by`` des blocs [MODEL] porte la politique
``ondelete`` de chaque arête entrante — le signal RAG des questions de
suppression du jalon 13. Amendement J11 (relevé R1) : la première ligne
de chaque bloc est une **synthèse générée en anglais** (clé
``synthesis`` — politique de langue CLAUDE.md §4 ter), déterministe
depuis les données FK (gabarit et gloses figés au plan § Formats),
jamais rédigée à la main.

Exécution : ``python -m scripts.generate_structural_metadata`` (second
temps de ``make rag-annotate``).
"""

# ─── IMPORTS ───
import sys
from pathlib import Path

import yaml

from scripts import corpus_analysis
from scripts.generate_topology_headers import format_field, format_list_field

# ──────────────

# [CODE_START]

FILE_MARKER_PREFIX: str = "# [FILE]"

MODEL_CLOSE: str = "# [/MODEL]"

MODEL_OPEN: str = "# [MODEL]"

SCHEMA_CLOSE: str = "# [/SCHEMA]"

SCHEMA_OPEN: str = "# [SCHEMA]"

POLICY_GLOSSES: dict[str, str] = {
    "CASCADE": "cascade-deleted",
    "RESTRICT": "blocked",
    "SET NULL": "unassigned",
}

TOPOLOGY_FILENAME: str = "TOPOLOGY.yaml"


def _entity_of_domain(models: tuple[corpus_analysis.ModelInfo, ...], domain: str) -> str:
    """Entité SQLAlchemy d'un domaine : le modèle de son module ``models``.

    Règle : le domaine de la phase 2 porte exactement un modèle ; ``none``
    est rendu si le module n'en déclare aucun (jamais une invention).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    entities: list[str]
    # ─────────────────────────────────────────

    # [STEP 1] Filtrer le registre par module → entité du domaine ou none
    entities = sorted(m.entity for m in models if m.module == f"{domain}.models")
    return ", ".join(entities) if entities else "none"


def _format_model_block(
    model: corpus_analysis.ModelInfo, referenced_by: dict[str, list[str]]
) -> list[str]:
    """Compose le bloc [MODEL] d'une entité, champs en ordre fixe.

    Ordre normatif (plan § Formats) : entity, table, columns, fks,
    referenced_by — ``fks`` rend ``colonne -> table.colonne [politique]``,
    ``referenced_by`` rend ``table.colonne -> politique`` (arêtes
    entrantes, signal RAG de la suppression).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    lines: list[str]
    # ─────────────────────────────────────────

    # [STEP 1] Assembler champs et marqueurs → synthèse anglaise en tête (J11, §4 ter)
    lines = [MODEL_OPEN]
    lines.extend(
        format_field("synthesis", _synthesis_of_model(model, referenced_by.get(model.table, [])))
    )
    lines.extend(format_field("entity", model.entity))
    lines.extend(format_field("table", model.table))
    lines.extend(format_list_field("columns", list(model.columns)))
    lines.extend(
        format_list_field("fks", [f"{fk.column} -> {fk.target} [{fk.policy}]" for fk in model.fks])
    )
    lines.extend(format_list_field("referenced_by", referenced_by.get(model.table, [])))
    lines.append(MODEL_CLOSE)
    return lines


def _format_schema_block(domain: str, classes: tuple[str, ...], entity: str) -> list[str]:
    """Compose le bloc [SCHEMA] d'un module de schémas, champs en ordre fixe.

    Ordre normatif (plan § Formats) : domain, schemas (classes triées avec
    leur base directe), entity (modèle SQLAlchemy correspondant).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    lines: list[str]
    # ─────────────────────────────────────────

    # [STEP 1] Assembler champs et marqueurs → synthèse anglaise en tête (J11, §4 ter)
    lines = [SCHEMA_OPEN]
    lines.extend(format_field("synthesis", _synthesis_of_schema(domain, classes, entity)))
    lines.extend(format_field("domain", domain))
    lines.extend(format_list_field("schemas", list(classes)))
    lines.extend(format_field("entity", entity))
    lines.append(SCHEMA_CLOSE)
    return lines


def _referenced_by_table(
    models: tuple[corpus_analysis.ModelInfo, ...],
) -> dict[str, list[str]]:
    """Arêtes FK entrantes par table cible, politiques ``ondelete`` incluses.

    Invariant : dérivé des seules déclarations ``ForeignKey`` du corpus —
    la carte inverse reflète exactement le graphe relationnel réel.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    referenced: dict[str, list[str]]
    target_table: str
    # ─────────────────────────────────────────

    # [STEP 1] Inverser chaque FK déclarée → entrantes triées par table cible
    referenced = {}
    for model in models:
        for fk in model.fks:
            target_table = fk.target.split(".")[0]
            referenced.setdefault(target_table, []).append(
                f"{model.table}.{fk.column} -> {fk.policy}"
            )
    return {table: sorted(entries) for table, entries in referenced.items()}


def _splice_file_blocks(
    path: Path, blocks: list[list[str]], open_marker: str, close_marker: str
) -> bool:
    """Remplace ou insère les blocs délimités d'un fichier, après ``# [FILE]``.

    Règles (R3, plan § Formats) : l'ancrage est la ligne suivant le
    marqueur ``# [FILE]`` — son absence est un échec explicite ; tout bloc
    existant à l'ancrage est intégralement retiré avant réinsertion.
    Retourne vrai si le fichier a réellement changé.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    anchor: int
    close_index: int
    lines: list[str]
    new_text: str
    original: str
    # ─────────────────────────────────────────

    # [STEP 1] Localiser l'ancrage sous # [FILE] → jamais d'insertion aveugle
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines()
    if not lines or not lines[0].startswith(FILE_MARKER_PREFIX):
        raise corpus_analysis.UnresolvedSymbolError(
            f"{path.as_posix()}:1 — marqueur {FILE_MARKER_PREFIX} absent, ancrage impossible"
        )
    anchor = 1

    # [STEP 2] Retirer les blocs existants à l'ancrage → remplacement, jamais d'accumulation
    while anchor < len(lines) and lines[anchor].strip() == open_marker:
        close_index = anchor
        while close_index < len(lines) and lines[close_index].strip() != close_marker:
            close_index += 1
        del lines[anchor : close_index + 1]

    # [STEP 3] Insérer les blocs régénérés et n'écrire qu'au changement → diffs stables
    lines[anchor:anchor] = [line for block in blocks for line in block]
    new_text = "\n".join(lines) + "\n"
    if new_text == original:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def _synthesis_of_model(model: corpus_analysis.ModelInfo, referenced: list[str]) -> str:
    """Synthèse anglaise d'un modèle, générée depuis ses arêtes entrantes.

    Gabarit figé (plan § Formats, amendement J11, langue §4 ter) :
    « A {Entity} is referenced by {table.column} ({policy} — {gloss}),
    … » — gloses figées par ``POLICY_GLOSSES`` ; sans arête entrante :
    « A {Entity} is not referenced by any table. » Jamais rédigée à la
    main.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    parts: list[str]
    policy: str
    source: str
    # ─────────────────────────────────────────

    # [STEP 1] Rendre chaque arête entrante avec sa glose → phrase déterministe
    if not referenced:
        return f"A {model.entity} is not referenced by any table."
    parts = []
    for entry in referenced:
        source, policy = entry.split(" -> ")
        parts.append(f"{source} ({policy} — {POLICY_GLOSSES.get(policy, policy)})")
    return f"A {model.entity} is referenced by {', '.join(parts)}."


def _synthesis_of_schema(domain: str, classes: tuple[str, ...], entity: str) -> str:
    """Synthèse anglaise d'un module de schémas — comptage et entité.

    Gabarit figé (plan § Formats, amendement J11, langue §4 ter) :
    « The {n} Pydantic schemas of the {domain} domain carry the contract
    of the {Entity} entity. » — accord déterministe du verbe sur le
    comptage (« carries » au singulier).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    head: str
    verb: str
    # ─────────────────────────────────────────

    # [STEP 1] Accorder tête et verbe sur le comptage → phrase déterministe
    head = "The Pydantic schema" if len(classes) == 1 else f"The {len(classes)} Pydantic schemas"
    verb = "carries" if len(classes) == 1 else "carry"
    return f"{head} of the {domain} domain {verb} the contract of the {entity} entity."


def _topology_payload(graph: corpus_analysis.CorpusGraph) -> dict[str, object]:
    """Charge utile de ``TOPOLOGY.yaml`` — graphe complet, listes pré-triées.

    Règle (R4) : ``sort_keys`` ne trie que les clés — chaque liste est
    triée explicitement ici ; aucun champ dépendant de l'environnement.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    functions: dict[str, dict[str, object]]
    # ─────────────────────────────────────────

    # [STEP 1] Rendre chaque nœud du graphe → entrées complètes et triées
    functions = {
        qualified: {
            "called_by": corpus_analysis.called_by_of(graph, qualified),
            "calls": corpus_analysis.calls_of(graph, qualified),
            "file": node.file,
            "mutates": sorted(graph.mutates.get(qualified, set())),
            "reads": sorted(graph.reads.get(qualified, set())),
            "tier": corpus_analysis.tier_of(graph, qualified),
            "weight": corpus_analysis.weight_of(graph, qualified),
        }
        for qualified, node in graph.functions.items()
    }
    return {"functions": functions}


def annotate_structure(app_dir: Path, topology_path: Path) -> list[str]:
    """Pose [MODEL]/[SCHEMA] et produit ``TOPOLOGY.yaml`` ; liste les modifiés.

    Règles métier :
    - blocs dérivés de l'analyse partagée (FR-001) — aucune logique AST
      propre à ce générateur ;
    - remplacement délimité : deux exécutions = diff vide (FR-002) ;
    - ``TOPOLOGY.yaml`` est identique octet pour octet entre deux
      générations sur corpus inchangé (FR-012, SC-002).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    changed: list[str]
    graph: corpus_analysis.CorpusGraph
    models: tuple[corpus_analysis.ModelInfo, ...]
    models_by_file: dict[str, list[corpus_analysis.ModelInfo]]
    referenced: dict[str, list[str]]
    schemas: dict[str, tuple[str, ...]]
    yaml_text: str
    # ─────────────────────────────────────────

    # [STEP 1] Collecter modèles et schémas via l'analyse partagée → matière des blocs
    models = corpus_analysis.collect_models(app_dir)
    referenced = _referenced_by_table(models)
    schemas = corpus_analysis.collect_schemas(app_dir)
    changed = []

    # [STEP 2] Poser les blocs [MODEL] fichier par fichier → un bloc par entité
    models_by_file = {}
    for model in models:
        models_by_file.setdefault(model.module, []).append(model)
    for module, entities in sorted(models_by_file.items()):
        path = app_dir / "domains" / module.split(".")[0] / "models.py"
        if _splice_file_blocks(
            path,
            [_format_model_block(m, referenced) for m in entities],
            MODEL_OPEN,
            MODEL_CLOSE,
        ):
            changed.append(path.as_posix())

    # [STEP 3] Poser les blocs [SCHEMA] → domaine, classes, entité du domaine
    for module, classes in sorted(schemas.items()):
        domain = module.split(".")[0]
        path = app_dir / "domains" / domain / "schemas.py"
        if _splice_file_blocks(
            path,
            [_format_schema_block(domain, classes, _entity_of_domain(models, domain))],
            SCHEMA_OPEN,
            SCHEMA_CLOSE,
        ):
            changed.append(path.as_posix())

    # [STEP 4] Sérialiser le graphe complet → TOPOLOGY.yaml déterministe (R4)
    graph = corpus_analysis.analyze_corpus(app_dir)
    yaml_text = yaml.safe_dump(
        _topology_payload(graph),
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=True,
    )
    if not topology_path.exists() or topology_path.read_text(encoding="utf-8") != yaml_text:
        topology_path.write_text(yaml_text, encoding="utf-8")
        changed.append(topology_path.as_posix())
    return changed


def main() -> None:
    """Point d'entrée CLI : structure ``app/`` + ``TOPOLOGY.yaml``, échec nommé.

    Règles métier :
    - tout échec d'analyse ou d'ancrage interrompt la génération avec son
      message exact — aucun bloc partiel n'est écrit dans ce cas ;
    - la sortie liste les fichiers modifiés (vide = structure déjà à jour).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    changed: list[str]
    # ─────────────────────────────────────────

    # [STEP 1] Générer la structure → échec explicite propagé en code retour 1
    try:
        changed = annotate_structure(Path("app"), Path(TOPOLOGY_FILENAME))
    except corpus_analysis.UnresolvedSymbolError as error:
        print(f"ÉCHEC structure : {error}", file=sys.stderr)
        raise SystemExit(1) from error

    # [STEP 2] Rendre compte → fichiers modifiés ou structure déjà à jour
    if changed:
        print("Métadonnées structurelles régénérées :")
        for file in changed:
            print(f"  {file}")
    else:
        print("Métadonnées structurelles à jour — aucun fichier modifié.")


if __name__ == "__main__":
    main()
