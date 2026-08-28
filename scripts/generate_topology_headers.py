# [FILE] — scripts/generate_topology_headers.py
"""Générateur des en-têtes [RAG] du corpus — consommateur de l'analyse T056.

Insère sur chaque fonction de premier niveau du corpus ``app/`` (hors
``models.py``/``schemas.py`` — périmètre CLAUDE.md §7 amendé) un bloc
``# [RAG]`` … ``# [/RAG]`` dérivé du graphe résolu : signature, tier,
weight, reads, mutates, puis calls/called_by en dernier (amendement J10
sur relevé R1 — le signal sémantique d'abord, l'annuaire ensuite) avec
plafond de 5 entrées et repli en synthèse déterministe, le graphe
intégral restant dans ``TOPOLOGY.yaml``. L'insertion est un remplacement
délimité (R3) : deux exécutions successives sur un code inchangé laissent
l'arbre strictement identique (FR-002). Les lignes longues sont repliées
sous 100 colonnes avec continuation ``#   `` (format normatif du plan).

Exécution : ``python -m scripts.generate_topology_headers`` (cible
``make rag-annotate``).
"""

# ─── IMPORTS ───
import ast
import sys
from pathlib import Path

from scripts import corpus_analysis

# ──────────────

# [CODE_START]

CONTINUATION_PREFIX: str = "#  "

HEADER_CLOSE: str = "# [/RAG]"

HEADER_LIST_CAP: int = 5

HEADER_OPEN: str = "# [RAG]"

MAX_LINE_LENGTH: int = 100


def _excluded_module(module: str) -> bool:
    """Vrai si le module est hors périmètre [RAG] (modèles et schémas).

    Règle (CLAUDE.md §7) : toute fonction du corpus hors ``models.py`` /
    ``schemas.py`` porte un en-tête — l'exclusion est structurelle, pas
    une liste de fichiers.
    """
    # [STEP 1] Tester le suffixe de module → modèles et schémas écartés
    return module.endswith(".models") or module.endswith(".schemas")


def _format_block(
    graph: corpus_analysis.CorpusGraph, node: corpus_analysis.FunctionNode
) -> list[str]:
    """Compose le bloc [RAG] complet d'une fonction, champs en ordre fixe.

    Ordre normatif (plan § Formats, amendé boucle J10 sur relevé R1) :
    signature, tier, weight, reads, mutates, puis calls/called_by en
    dernier — listes triées ASCII, ``none`` si vide, plafond de
    ``HEADER_LIST_CAP`` entrées avec repli en synthèse déterministe.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    lines: list[str]
    # ─────────────────────────────────────────

    # [STEP 1] Assembler champs et marqueurs → signal sémantique d'abord, annuaire ensuite
    lines = [HEADER_OPEN]
    lines.extend(format_field("signature", node.signature))
    lines.extend(format_field("tier", corpus_analysis.tier_of(graph, node.qualified)))
    lines.extend(format_field("weight", str(corpus_analysis.weight_of(graph, node.qualified))))
    lines.extend(format_list_field("reads", sorted(graph.reads.get(node.qualified, set()))))
    lines.extend(format_list_field("mutates", sorted(graph.mutates.get(node.qualified, set()))))
    lines.extend(
        _format_call_field("calls", "outbound", corpus_analysis.calls_of(graph, node.qualified))
    )
    lines.extend(
        _format_call_field(
            "called_by", "inbound", corpus_analysis.called_by_of(graph, node.qualified)
        )
    )
    lines.append(HEADER_CLOSE)
    return lines


def _format_call_field(label: str, direction: str, values: list[str]) -> list[str]:
    """Rend un champ d'appels plafonné — liste courte ou synthèse déterministe.

    Règle (plan § Formats, amendement J10 ; gabarit anglais depuis la
    politique de langue CLAUDE.md §4 ter) : au-delà de
    ``HEADER_LIST_CAP`` entrées, l'en-tête porte le résumé
    « N {direction} calls — M domains (liste triée) — details:
    TOPOLOGY.yaml » ; le graphe intégral reste dans ``TOPOLOGY.yaml``.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    domains: list[str]
    summary: str
    # ─────────────────────────────────────────

    # [STEP 1] Garder la liste courte telle quelle → cas nominal inchangé
    if len(values) <= HEADER_LIST_CAP:
        return format_list_field(label, values)

    # [STEP 2] Replier en synthèse déterministe → l'en-tête reste un résumé
    domains = sorted({value.split(".")[0] for value in values})
    summary = (
        f"{len(values)} {direction} calls — {len(domains)} domain"
        f"{'s' if len(domains) > 1 else ''} ({', '.join(domains)}) — details: TOPOLOGY.yaml"
    )
    return format_field(label, summary)


def _module_functions(path: Path) -> list[tuple[str, int]]:
    """Fonctions de premier niveau d'un fichier : (nom, ligne d'ancrage).

    L'ancrage est la première ligne du bloc décoré — le point exact où le
    bloc [RAG] s'insère (plan § Formats).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    functions: list[tuple[str, int]]
    statement: ast.stmt
    tree: ast.Module
    # ─────────────────────────────────────────

    # [STEP 1] Parser le fichier et relever chaque fonction → ancrages exacts
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    functions = []
    for statement in tree.body:
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef):
            functions.append(
                (
                    statement.name,
                    statement.decorator_list[0].lineno
                    if statement.decorator_list
                    else statement.lineno,
                )
            )
    return functions


def _splice_block(lines: list[str], anchor_index: int, block: list[str]) -> None:
    """Remplace ou insère un bloc [RAG] à un ancrage donné, en place.

    Règle (R3) : tout bloc délimité existant immédiatement au-dessus de
    l'ancrage est intégralement retiré avant réinsertion — jamais
    d'accumulation, quel que soit son contenu antérieur.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    open_index: int
    start: int
    # ─────────────────────────────────────────

    # [STEP 1] Retirer le bloc existant adjacent → ancrage ramené à nu
    start = anchor_index
    if start > 0 and lines[start - 1].strip() == HEADER_CLOSE:
        open_index = start - 1
        while open_index >= 0 and lines[open_index].strip() != HEADER_OPEN:
            open_index -= 1
        del lines[open_index:start]
        start = open_index

    # [STEP 2] Insérer le bloc régénéré → en-tête contigu à la fonction
    lines[start:start] = block


def annotate_corpus(app_dir: Path) -> list[str]:
    """Annote tout le corpus et retourne les chemins des fichiers modifiés.

    Règles métier :
    - périmètre = toutes les fonctions de premier niveau hors modèles et
      schémas (FR-010, CLAUDE.md §7) ;
    - remplacement délimité par marqueurs — l'idempotence se lit au diff
      vide (FR-002, cible ``rag-check``) ;
    - un fichier n'est réécrit que si son contenu change (diffs stables).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    block: list[str]
    changed: list[str]
    graph: corpus_analysis.CorpusGraph
    lines: list[str]
    new_text: str
    node: corpus_analysis.FunctionNode
    nodes: list[corpus_analysis.FunctionNode]
    original: str
    path: Path
    # ─────────────────────────────────────────

    # [STEP 1] Analyser le corpus → graphe résolu, source unique des en-têtes
    graph = corpus_analysis.analyze_corpus(app_dir)

    # [STEP 2] Traiter chaque fichier porteur, de bas en haut → ancrages stables
    changed = []
    for path in sorted({Path(n.file) for n in graph.functions.values()}):
        nodes = [
            n
            for n in graph.functions.values()
            if Path(n.file) == path and not _excluded_module(n.module)
        ]
        if not nodes:
            continue
        original = path.read_text(encoding="utf-8")
        lines = original.splitlines()
        anchors = dict(_module_functions(path))
        for node in sorted(nodes, key=lambda item: anchors[item.name], reverse=True):
            block = _format_block(graph, node)
            _splice_block(lines, anchors[node.name] - 1, block)

        # [STEP 3] N'écrire qu'en cas de changement → deux passes = diff vide
        new_text = "\n".join(lines) + "\n"
        if new_text != original:
            path.write_text(new_text, encoding="utf-8")
            changed.append(path.as_posix())
    return changed


def format_field(label: str, value: str) -> list[str]:
    """Rend un champ ``# label: valeur`` replié sous la borne de colonnes.

    Le repli coupe sur les séparateurs ``, `` puis, à défaut de virgule
    (phrases de synthèse), sur le dernier espace sous la borne ; les
    lignes de continuation portent le préfixe ``#  `` — le champ reste
    parsable ligne à ligne (plan § Formats, règle précisée le 2026-08-28).
    API partagée : le générateur structurel (jalon 11) consomme le même
    repli pour les blocs [MODEL]/[SCHEMA] — une seule définition du format.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    current: str
    cut: int
    lines: list[str]
    segment: str
    segments: list[str]
    wrapped: list[str]
    # ─────────────────────────────────────────

    # [STEP 1] Retourner tel quel un champ court → cas nominal sans repli
    current = f"# {label}: {value}"
    if len(current) <= MAX_LINE_LENGTH:
        return [current]

    # [STEP 2] Replier sur les virgules → lignes bornées, contenu intact
    segments = value.split(", ")
    lines = []
    current = f"# {label}: {segments[0]}"
    for segment in segments[1:]:
        if len(f"{current}, {segment}") <= MAX_LINE_LENGTH:
            current = f"{current}, {segment}"
        else:
            lines.append(f"{current},")
            current = f"{CONTINUATION_PREFIX} {segment}"
    lines.append(current)

    # [STEP 3] Replier sur l'espace à défaut de virgule → aucune ligne hors borne
    wrapped = []
    for line in lines:
        while len(line) > MAX_LINE_LENGTH:
            cut = line.rfind(" ", len(CONTINUATION_PREFIX) + 2, MAX_LINE_LENGTH + 1)
            if cut <= 0:
                break
            wrapped.append(line[:cut])
            line = f"{CONTINUATION_PREFIX} {line[cut + 1 :]}"
        wrapped.append(line)
    return wrapped


def format_list_field(label: str, values: list[str]) -> list[str]:
    """Rend un champ liste — éléments triés joints par ``, ``, ``none`` si vide."""
    # [STEP 1] Joindre ou marquer l'absence → champ toujours présent
    return format_field(label, ", ".join(values) if values else "none")


def main() -> None:
    """Point d'entrée CLI : annote ``app/`` et rend compte, échec nommé sinon.

    Règles métier :
    - tout symbole non résolu interrompt la génération avec son message
      exact (FR-007) — aucun en-tête partiel n'est écrit dans ce cas ;
    - la sortie liste les fichiers modifiés (vide = corpus déjà à jour).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    changed: list[str]
    # ─────────────────────────────────────────

    # [STEP 1] Annoter le corpus → échec explicite propagé en code retour 1
    try:
        changed = annotate_corpus(Path("app"))
    except corpus_analysis.UnresolvedSymbolError as error:
        print(f"ÉCHEC topologie : {error}", file=sys.stderr)
        raise SystemExit(1) from error

    # [STEP 2] Rendre compte → fichiers modifiés ou corpus déjà à jour
    if changed:
        print("En-têtes [RAG] régénérés :")
        for file in changed:
            print(f"  {file}")
    else:
        print("En-têtes [RAG] à jour — aucun fichier modifié.")


if __name__ == "__main__":
    main()
