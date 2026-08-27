# [FILE] — scripts/corpus_analysis.py
"""Analyse AST partagée du corpus ``app/`` — graphe d'appels, weight, tier.

Module d'analyse pure consommé par les deux générateurs d'annotations
(T056, arbitrage d'ouverture de phase 3) : il lit le corpus, ne modifie
aucun fichier. Règles du graphe (research.md R1–R2, figées) :

- ``weight`` = appels entrants + appels sortants dans le graphe résolu ;
- ``LEAF`` = 0 appel entrant hors de son routeur ; ``CORE`` = référencé par
  au moins un service ou le seed ; ``CRITICAL_CORE`` = ``get_db``,
  ``settings``, et toute fonction référencée par 3 domaines ou plus ;
- ``Depends(f)`` et toute référence à une fonction du corpus passée en
  argument créent une arête entrante vers ``f`` (réalité d'exécution) ;
- les appels via alias de module sont résolus vers leur cible réelle ;
- tout symbole appelé ou importé non résolu est un échec explicite,
  jamais un en-tête silencieusement incomplet.

Décisions d'implémentation dérivées (sans étendre la sémantique) : les
nœuds du graphe sont les fonctions de premier niveau des modules ; le
singleton ``settings`` est suivi comme entité lue (``reads``) et nœud à
part ; les fonctions imbriquées appartiennent au fragment de leur parent.
"""

# ─── IMPORTS ───
import ast
import builtins
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

# ──────────────

# [CODE_START]

SETTINGS_QUALIFIED: str = "core.config.settings"

NAMED_CRITICAL_CORE: frozenset[str] = frozenset({"core.database.get_db", SETTINGS_QUALIFIED})

_BUILTIN_NAMES: frozenset[str] = frozenset(dir(builtins))


class UnresolvedSymbolError(Exception):
    """Symbole appelé ou importé qui ne se résout vers aucune cible connue.

    Porte le fichier, la ligne et le symbole en clair : l'échec de
    résolution est un résultat nommé (FR-007), jamais un silence.
    """


@dataclass(frozen=True)
class FunctionNode:
    """Fonction de premier niveau du corpus — un nœud du graphe d'appels."""

    anchor_lineno: int
    file: str
    lineno: int
    module: str
    name: str
    qualified: str
    signature: str


@dataclass
class CorpusGraph:
    """Résultat complet de l'analyse — graphe résolu et empreintes d'accès."""

    edges: set[tuple[str, str]] = field(default_factory=set)
    functions: dict[str, FunctionNode] = field(default_factory=dict)
    mutates: dict[str, set[str]] = field(default_factory=dict)
    reads: dict[str, set[str]] = field(default_factory=dict)
    settings_readers: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class ForeignKeyInfo:
    """Arête FK déclarée par un modèle — colonne, cible et politique ``ondelete``."""

    column: str
    policy: str
    target: str


@dataclass(frozen=True)
class ModelInfo:
    """Structure d'un modèle SQLAlchemy du corpus — matière du bloc [MODEL]."""

    columns: tuple[str, ...]
    entity: str
    fks: tuple[ForeignKeyInfo, ...]
    module: str
    table: str


@dataclass(frozen=True)
class _ModuleContext:
    """Contexte de résolution d'un module — alias, symboles, univers corpus."""

    aliases: dict[str, str]
    file: str
    functions: frozenset[str]
    model_tables: dict[str, str]
    module: str
    modules: frozenset[str]
    symbols: dict[str, frozenset[str]]


def _anchor_lineno(func: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Ligne d'ancrage d'un en-tête [RAG] : premier décorateur, sinon ``def``.

    Invariant : l'ancrage précède toujours la totalité du bloc de la
    fonction — le fragment RAG (en-tête + fonction) reste contigu.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    lineno: int
    # ─────────────────────────────────────────

    # [STEP 1] Choisir la première ligne du bloc décoré → ancrage stable
    lineno = func.decorator_list[0].lineno if func.decorator_list else func.lineno
    return lineno


def _build_signature(func: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Reconstruit ``nom(param: T, ...) -> R`` depuis l'AST, défauts compris.

    Règles : paramètres positionnels puis keyword-only (séparateur ``*``
    unique), annotations et défauts rendus par ``ast.unparse`` — la
    signature est dérivée du code réel, jamais copiée.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    argument: ast.arg
    default: ast.expr | None
    defaults: dict[int, ast.expr]
    index: int
    parts: list[str]
    rendered: str
    returns: str
    # ─────────────────────────────────────────

    # [STEP 1] Aligner les défauts positionnels sur la fin des arguments → index exacts
    defaults = {
        len(func.args.args) - len(func.args.defaults) + offset: value
        for offset, value in enumerate(func.args.defaults)
    }

    # [STEP 2] Rendre chaque paramètre positionnel → annotation et défaut inclus
    parts = []
    for index, argument in enumerate(func.args.args):
        rendered = argument.arg
        if argument.annotation is not None:
            rendered = f"{rendered}: {ast.unparse(argument.annotation)}"
        if index in defaults:
            rendered = f"{rendered} = {ast.unparse(defaults[index])}"
        parts.append(rendered)

    # [STEP 3] Rendre les keyword-only après un séparateur unique → même forme
    if func.args.kwonlyargs:
        parts.append("*")
    for argument, default in zip(func.args.kwonlyargs, func.args.kw_defaults, strict=True):
        rendered = argument.arg
        if argument.annotation is not None:
            rendered = f"{rendered}: {ast.unparse(argument.annotation)}"
        if default is not None:
            rendered = f"{rendered} = {ast.unparse(default)}"
        parts.append(rendered)

    # [STEP 4] Assembler avec le retour annoté → signature complète et déterministe
    returns = f" -> {ast.unparse(func.returns)}" if func.returns is not None else ""
    return f"{func.name}({', '.join(parts)}){returns}"


def _collect_aliases(tree: ast.Module) -> dict[str, str]:
    """Table des alias d'un module : nom local → cible pointée complète.

    Couvre ``import a.b as c`` (c → a.b) et ``from m import x as y``
    (y → m.x) — la résolution vers le corpus se fait au point d'usage.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    aliases: dict[str, str]
    statement: ast.stmt
    # ─────────────────────────────────────────

    # [STEP 1] Parcourir les imports de premier niveau → table locale complète
    aliases = {}
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            for name in statement.names:
                aliases[name.asname or name.name.split(".")[0]] = (
                    name.name if name.asname else name.name.split(".")[0]
                )
        elif isinstance(statement, ast.ImportFrom) and statement.module is not None:
            for name in statement.names:
                aliases[name.asname or name.name] = f"{statement.module}.{name.name}"
    return aliases


def _collect_called_name_ids(func: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[int]:
    """Identifiants des nœuds ``Name`` occupant la position d'appel direct."""
    # [STEP 1] Relever chaque fonction d'appel nominale → positions d'appel connues
    return frozenset(
        id(node.func)
        for node in _walk_runtime(func)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    )


def _collect_class_columns(cls: ast.ClassDef) -> list[str]:
    """Colonnes d'un modèle : attributs annotés ``Mapped[...]``, triés ASCII.

    Invariant du corpus : toute colonne est déclarée en ``Mapped`` — la
    liste dérive de la structure, jamais d'une énumération manuelle.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    columns: list[str]
    statement: ast.stmt
    # ─────────────────────────────────────────

    # [STEP 1] Relever chaque attribut Mapped → colonnes triées de la table
    columns = []
    for statement in cls.body:
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            if any(
                isinstance(node, ast.Name) and node.id == "Mapped"
                for node in ast.walk(statement.annotation)
            ):
                columns.append(statement.target.id)
    return sorted(columns)


def _collect_class_fks(cls: ast.ClassDef) -> list[ForeignKeyInfo]:
    """FK d'un modèle : appels ``ForeignKey`` des colonnes, politique incluse.

    Règles : la cible est le premier argument constant (``table.colonne``) ;
    la politique vient du mot-clé ``ondelete`` — ``NO ACTION`` si absent
    (défaut SQL), jamais une valeur inventée.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    fks: list[ForeignKeyInfo]
    node: ast.AST
    policy: str
    statement: ast.stmt
    # ─────────────────────────────────────────

    # [STEP 1] Chercher ForeignKey dans chaque colonne → arête complète par appel
    fks = []
    for statement in cls.body:
        if not (isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)):
            continue
        for node in ast.walk(statement):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "ForeignKey"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                policy = "NO ACTION"
                for keyword in node.keywords:
                    if keyword.arg == "ondelete" and isinstance(keyword.value, ast.Constant):
                        policy = str(keyword.value.value)
                fks.append(
                    ForeignKeyInfo(
                        column=statement.target.id, policy=policy, target=node.args[0].value
                    )
                )
    return sorted(fks, key=lambda fk: fk.column)


def _collect_local_model_types(
    func: ast.FunctionDef | ast.AsyncFunctionDef, model_tables: dict[str, str]
) -> dict[str, str]:
    """Types modèles des variables locales, lus dans la Zone B (AnnAssign).

    Invariant du corpus : toute variable locale est déclarée et typée en
    Zone B — la table variable → table SQL en découle sans inférence.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    local_types: dict[str, str]
    statement: ast.stmt
    # ─────────────────────────────────────────

    # [STEP 1] Lire chaque déclaration annotée → variable liée à sa table modèle
    local_types = {}
    for statement in func.body:
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            for node in ast.walk(statement.annotation):
                if isinstance(node, ast.Name) and node.id in model_tables:
                    local_types[statement.target.id] = model_tables[node.id]
    return local_types


def _collect_model_tables(trees: dict[str, ast.Module]) -> dict[str, str]:
    """Registre des modèles du corpus : nom de classe → nom de table.

    Un modèle est toute classe portant un ``__tablename__`` constant —
    la détection est structurelle, indépendante du fichier porteur.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    statement: ast.stmt
    tables: dict[str, str]
    # ─────────────────────────────────────────

    # [STEP 1] Balayer les classes de tous les modules → registre complet
    tables = {}
    for tree in trees.values():
        for statement in tree.body:
            if not isinstance(statement, ast.ClassDef):
                continue
            for inner in statement.body:
                if (
                    isinstance(inner, ast.Assign)
                    and any(
                        isinstance(target, ast.Name) and target.id == "__tablename__"
                        for target in inner.targets
                    )
                    and isinstance(inner.value, ast.Constant)
                    and isinstance(inner.value.value, str)
                ):
                    tables[statement.name] = inner.value.value
    return tables


def _collect_module_symbols(tree: ast.Module) -> frozenset[str]:
    """Noms définis au premier niveau d'un module (fonctions, classes, constantes)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    statement: ast.stmt
    symbols: set[str]
    # ─────────────────────────────────────────

    # [STEP 1] Relever chaque définition de premier niveau → univers des symboles
    symbols = set()
    for statement in tree.body:
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            symbols.add(statement.name)
        elif isinstance(statement, ast.Assign):
            symbols.update(
                target.id for target in statement.targets if isinstance(target, ast.Name)
            )
        elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            symbols.add(statement.target.id)
    return frozenset(symbols)


def _domain_of(qualified: str) -> str:
    """Segment de tête d'un nom qualifié — domaine ou module hors-domaines.

    ``users.services.create_user`` → ``users`` ; ``core.database.get_db``
    → ``core`` ; ``scripts.seed.run`` → ``scripts`` ; ``main.create_app``
    → ``main`` (R1 : core, scripts et main comptent comme modules
    hors-domaines dans le comptage « 3+ domaines »).
    """
    # [STEP 1] Extraire le premier segment → domaine d'appartenance
    return qualified.split(".")[0]


def _module_qualified(app_dir: Path, path: Path) -> str:
    """Nom qualifié corpus d'un fichier : relatif à ``app/``, sans ``domains``.

    ``app/domains/users/services.py`` → ``users.services`` ;
    ``app/core/database.py`` → ``core.database`` ; ``app/main.py`` →
    ``main`` ; les ``__init__.py`` prennent le nom de leur paquet.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    parts: list[str]
    # ─────────────────────────────────────────

    # [STEP 1] Décomposer le chemin relatif → segments sans suffixe ni __init__
    parts = list(path.relative_to(app_dir).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()

    # [STEP 2] Effacer le niveau technique domains → noms au format domaine.module
    if parts and parts[0] == "domains":
        parts.pop(0)
    return ".".join(parts) if parts else "app"


def _normalize_target(dotted: str) -> str:
    """Projette une cible d'import ``app.*`` dans l'espace qualifié corpus.

    ``app.domains.users.services.create_user`` → ``users.services.create_user`` ;
    une cible hors ``app.*`` est rendue telle quelle (externe au corpus).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    parts: list[str]
    # ─────────────────────────────────────────

    # [STEP 1] Réduire le préfixe app.domains → espace de noms du corpus
    if dotted != "app" and not dotted.startswith("app."):
        return dotted
    parts = dotted.split(".")[1:]
    if parts and parts[0] == "domains":
        parts.pop(0)
    return ".".join(parts)


def _parse_corpus(app_dir: Path) -> tuple[dict[str, ast.Module], dict[str, str]]:
    """Parse le corpus dans l'ordre déterministe des chemins (R6).

    Invariant : la découverte est ``sorted(rglob)`` — mêmes fichiers,
    même ordre, mêmes résultats, sur toute machine. Retourne les AST et
    la table module qualifié → chemin POSIX réel (messages d'échec).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    files: dict[str, str]
    module: str
    path: Path
    trees: dict[str, ast.Module]
    # ─────────────────────────────────────────

    # [STEP 1] Lire et parser chaque fichier trié → un AST par module qualifié
    files = {}
    trees = {}
    for path in sorted(app_dir.rglob("*.py")):
        module = _module_qualified(app_dir, path)
        files[module] = path.as_posix()
        trees[module] = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return trees, files


def _resolve_attribute(node: ast.Attribute, context: _ModuleContext) -> str | None:
    """Résout ``base.attr`` — arête si la cible est une fonction du corpus.

    Règles : base aliasée vers un module du corpus → l'attribut doit y
    exister (sinon échec explicite) ; base aliasée vers un module externe
    ou nom local → appel de méthode, hors graphe.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    qualified: str
    target: str
    # ─────────────────────────────────────────

    # [STEP 1] Ne traiter que base nominale aliasée → le reste est méthode locale
    if not isinstance(node.value, ast.Name) or node.value.id not in context.aliases:
        return None
    target = _normalize_target(context.aliases[node.value.id])
    if target not in context.modules:
        return None

    # [STEP 2] Exiger l'existence de l'attribut dans le module corpus → jamais de silence
    qualified = f"{target}.{node.attr}"
    if node.attr not in context.symbols[target]:
        raise UnresolvedSymbolError(
            f"{context.file}:{node.lineno} — symbole non résolu : {qualified}"
        )
    return qualified if qualified in context.functions else None


def _resolve_function(
    func: ast.FunctionDef | ast.AsyncFunctionDef, context: _ModuleContext, graph: CorpusGraph
) -> None:
    """Collecte arêtes, ``reads`` et ``mutates`` d'une fonction du corpus.

    Règles : toute référence à une fonction corpus (appel direct, alias,
    ``Depends``, callback) crée une arête ; ``settings`` est une entité
    lue ; les mutations suivent ``db.add``/``db.delete``/``setattr``/
    écriture d'attribut sur variable typée modèle (Zone B).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    called_ids: frozenset[int]
    constructor_ids: frozenset[int]
    local_types: dict[str, str]
    node: ast.AST
    source: str
    target: str | None
    # ─────────────────────────────────────────

    # [STEP 1] Préparer le cadre local → clé source, types Zone B, positions d'appel
    source = f"{context.module}.{func.name}"
    local_types = _collect_local_model_types(func, context.model_tables)
    called_ids = _collect_called_name_ids(func)
    graph.mutates.setdefault(source, set())
    graph.reads.setdefault(source, set())

    # [STEP 2] Exclure les constructeurs de modèles du champ reads → écrits, pas lus
    constructor_ids = frozenset(
        id(node.func)
        for node in _walk_runtime(func)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in context.model_tables
    )

    # [STEP 3] Balayer les nœuds runtime → arêtes, entités lues, tables mutées
    for node in _walk_runtime(func):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            target = _resolve_name(node, context, called=id(node) in called_ids)
            if target is not None:
                graph.edges.add((source, target))
            if context.aliases.get(node.id) == "app.core.config.settings":
                graph.reads[source].add("settings")
                graph.settings_readers.add(source)
            if node.id in context.model_tables and id(node) not in constructor_ids:
                graph.reads[source].add(context.model_tables[node.id])
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
            target = _resolve_attribute(node, context)
            if target is not None:
                graph.edges.add((source, target))
        _resolve_mutation(node, local_types, graph.mutates[source])


def _resolve_mutation(node: ast.AST, local_types: dict[str, str], mutated: set[str]) -> None:
    """Détecte une mutation de table portée par un nœud AST unique.

    Règles : ``db.add(var)`` / ``db.delete(var)``, ``setattr(var, ...)``
    et l'affectation d'attribut ``var.champ = ...`` mutent la table de
    ``var`` — ``var`` étant typée modèle en Zone B (invariant du corpus).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    first: ast.expr
    target: ast.expr
    # ─────────────────────────────────────────

    # [STEP 1] Reconnaître db.add/db.delete/setattr → table de l'argument muté
    if isinstance(node, ast.Call) and node.args:
        first = node.args[0]
        if isinstance(first, ast.Name) and first.id in local_types:
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in {"add", "delete"}
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "db"
            ) or (isinstance(node.func, ast.Name) and node.func.id == "setattr"):
                mutated.add(local_types[first.id])

    # [STEP 2] Reconnaître l'affectation d'attribut → table de la variable cible
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id in local_types
            ):
                mutated.add(local_types[target.value.id])


def _resolve_name(node: ast.Name, context: _ModuleContext, called: bool) -> str | None:
    """Résout un nom chargé — arête si fonction corpus, échec si appel inconnu.

    Règles : alias d'import → cible réelle ; symbole du module courant →
    qualifié local ; un nom **appelé** qui n'est ni alias, ni symbole du
    module, ni builtin est un échec explicite (les simples chargements
    restent des variables locales, légitimes).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    qualified: str
    # ─────────────────────────────────────────

    # [STEP 1] Résoudre par alias d'import → fonction corpus = arête, sinon connu
    if node.id in context.aliases:
        qualified = _normalize_target(context.aliases[node.id])
        return qualified if qualified in context.functions else None

    # [STEP 2] Résoudre dans le module courant → fonctions locales reliées
    if node.id in context.symbols[context.module]:
        qualified = f"{context.module}.{node.id}"
        return qualified if qualified in context.functions else None

    # [STEP 3] Refuser un appel non résolu → builtins et variables locales exclus
    if called and node.id not in _BUILTIN_NAMES:
        raise UnresolvedSymbolError(f"{context.file}:{node.lineno} — appel non résolu : {node.id}")
    return None


def _validate_imports(
    tree: ast.Module,
    file: str,
    modules: frozenset[str],
    symbols: dict[str, frozenset[str]],
) -> None:
    """Vérifie que chaque import ``app.*`` du module cible une entité réelle.

    Règles (FR-007) : un import de module doit viser un module du corpus ;
    un ``from`` doit viser un sous-module ou un symbole de premier niveau
    de sa cible ; l'import relatif est hors standard — tout écart est un
    échec nommé, jamais ignoré.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    normalized: str
    statement: ast.stmt
    # ─────────────────────────────────────────

    for statement in tree.body:
        # [STEP 1] Contrôler les imports de modules → cible présente dans le corpus
        if isinstance(statement, ast.Import):
            for name in statement.names:
                if name.name == "app" or name.name.startswith("app."):
                    if _normalize_target(name.name) not in modules:
                        raise UnresolvedSymbolError(
                            f"{file}:{statement.lineno} — module non résolu : {name.name}"
                        )

        # [STEP 2] Contrôler les from-imports → sous-module ou symbole existant
        elif isinstance(statement, ast.ImportFrom):
            if statement.level:
                raise UnresolvedSymbolError(
                    f"{file}:{statement.lineno} — import relatif hors standard corpus"
                )
            if statement.module is None or not statement.module.startswith("app"):
                continue
            normalized = _normalize_target(statement.module)
            for name in statement.names:
                if f"{normalized}.{name.name}" in modules or (
                    normalized in modules and name.name in symbols[normalized]
                ):
                    continue
                raise UnresolvedSymbolError(
                    f"{file}:{statement.lineno} — symbole non résolu : "
                    f"{statement.module}.{name.name}"
                )


def _walk_runtime(node: ast.AST) -> Iterator[ast.AST]:
    """Parcourt les nœuds exécutables d'une fonction, annotations exclues.

    Règles : les annotations (paramètres, retours, Zone B) sont du typage,
    pas des références d'exécution — elles ne créent ni arête ni lecture ;
    les défauts de paramètres (``Depends(...)``) et les décorateurs sont
    exécutés, donc inclus ; les fonctions imbriquées sont traversées.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    child: ast.AST
    stack: list[ast.AST]
    # ─────────────────────────────────────────

    # [STEP 1] Descendre en profondeur en élaguant les annotations → runtime seul
    stack = [node]
    while stack:
        child = stack.pop()
        if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
            stack.extend(child.decorator_list)
            stack.extend(child.args.defaults)
            stack.extend(part for part in child.args.kw_defaults if part is not None)
            stack.extend(child.body)
        elif isinstance(child, ast.AnnAssign):
            stack.extend(part for part in (child.target, child.value) if part is not None)
        elif isinstance(child, ast.arg):
            continue
        else:
            yield child
            stack.extend(ast.iter_child_nodes(child))


def analyze_corpus(app_dir: Path) -> CorpusGraph:
    """Analyse complète du corpus : nœuds, arêtes résolues, reads/mutates.

    Règles métier :
    - zéro import non résolu — tout échec lève ``UnresolvedSymbolError``
      nommant fichier, ligne et symbole (FR-007) ;
    - le graphe encode la réalité d'exécution : ``Depends`` et callbacks
      créent des arêtes entrantes (R2) ;
    - le résultat est déterministe : fichiers triés, structures reproduites
      à l'identique sur corpus inchangé (R6).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    context: _ModuleContext
    files: dict[str, str]
    graph: CorpusGraph
    model_tables: dict[str, str]
    modules: frozenset[str]
    symbols: dict[str, frozenset[str]]
    trees: dict[str, ast.Module]
    # ─────────────────────────────────────────

    # [STEP 1] Parser le corpus et bâtir les univers → modules, symboles, modèles
    trees, files = _parse_corpus(app_dir)
    modules = frozenset(trees)
    symbols = {module: _collect_module_symbols(tree) for module, tree in trees.items()}
    model_tables = _collect_model_tables(trees)

    # [STEP 2] Recenser les nœuds fonctions → un nœud par fonction de premier niveau
    graph = CorpusGraph()
    for module, tree in sorted(trees.items()):
        for statement in tree.body:
            if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef):
                graph.functions[f"{module}.{statement.name}"] = FunctionNode(
                    anchor_lineno=_anchor_lineno(statement),
                    file=files[module],
                    lineno=statement.lineno,
                    module=module,
                    name=statement.name,
                    qualified=f"{module}.{statement.name}",
                    signature=_build_signature(statement),
                )

    # [STEP 3] Valider les imports puis résoudre chaque fonction → graphe complet
    for module, tree in sorted(trees.items()):
        context = _ModuleContext(
            aliases=_collect_aliases(tree),
            file=files[module],
            functions=frozenset(graph.functions),
            model_tables=model_tables,
            module=module,
            modules=modules,
            symbols=symbols,
        )
        _validate_imports(tree, files[module], modules, symbols)
        for statement in tree.body:
            if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef):
                _resolve_function(statement, context, graph)
    return graph


def called_by_of(graph: CorpusGraph, qualified: str) -> list[str]:
    """Appelants triés d'une fonction dans le graphe résolu."""
    # [STEP 1] Filtrer les arêtes entrantes → liste triée déterministe
    return sorted(source for source, target in graph.edges if target == qualified)


def calls_of(graph: CorpusGraph, qualified: str) -> list[str]:
    """Fonctions appelées, triées, par une fonction du graphe résolu."""
    # [STEP 1] Filtrer les arêtes sortantes → liste triée déterministe
    return sorted(target for source, target in graph.edges if source == qualified)


def collect_models(app_dir: Path) -> tuple[ModelInfo, ...]:
    """Structures des modèles du corpus, triées par (module, entité).

    Règles métier :
    - un modèle = une classe portant ``__tablename__`` (même critère que
      le registre du graphe — une seule définition de la notion) ;
    - colonnes et FK dérivent de l'AST : le bloc [MODEL] n'énonce que ce
      que le code déclare (FR-001).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    models: list[ModelInfo]
    statement: ast.stmt
    tables: dict[str, str]
    trees: dict[str, ast.Module]
    # ─────────────────────────────────────────

    # [STEP 1] Parser le corpus et croiser le registre → une entrée par modèle
    trees, _ = _parse_corpus(app_dir)
    tables = _collect_model_tables(trees)
    models = []
    for module, tree in sorted(trees.items()):
        for statement in tree.body:
            if isinstance(statement, ast.ClassDef) and statement.name in tables:
                models.append(
                    ModelInfo(
                        columns=tuple(_collect_class_columns(statement)),
                        entity=statement.name,
                        fks=tuple(_collect_class_fks(statement)),
                        module=module,
                        table=tables[statement.name],
                    )
                )
    return tuple(sorted(models, key=lambda model: (model.module, model.entity)))


def collect_schemas(app_dir: Path) -> dict[str, tuple[str, ...]]:
    """Classes de schémas par module ``*.schemas`` : ``Nom(BaseDirecte)`` triés.

    Règle : la base rendue est la première base déclarée (héritage direct),
    dérivée de l'AST — le bloc [SCHEMA] reflète la hiérarchie réelle.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    entries: list[str]
    schemas: dict[str, tuple[str, ...]]
    statement: ast.stmt
    trees: dict[str, ast.Module]
    # ─────────────────────────────────────────

    # [STEP 1] Balayer les modules de schémas → classes rendues avec leur base
    trees, _ = _parse_corpus(app_dir)
    schemas = {}
    for module, tree in sorted(trees.items()):
        if not module.endswith(".schemas"):
            continue
        entries = []
        for statement in tree.body:
            if isinstance(statement, ast.ClassDef):
                entries.append(
                    f"{statement.name}({ast.unparse(statement.bases[0])})"
                    if statement.bases
                    else statement.name
                )
        schemas[module] = tuple(sorted(entries))
    return schemas


def tier_of(graph: CorpusGraph, qualified: str) -> str:
    """Classe un nœud sur l'échelle fermée LEAF / CORE / CRITICAL_CORE (R1).

    Règles figées : membres nommés (``get_db``, ``settings``) et fonctions
    référencées par 3+ domaines → CRITICAL_CORE ; référencé par un service
    ou le seed → CORE ; sinon LEAF — le niveau le plus élevé l'emporte.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    callers: list[str]
    domains: set[str]
    # ─────────────────────────────────────────

    # [STEP 1] Trancher les membres nommés → cœur critique par décision figée
    if qualified in NAMED_CRITICAL_CORE:
        return "CRITICAL_CORE"

    # [STEP 2] Compter les domaines appelants distincts → 3+ = cœur critique
    callers = called_by_of(graph, qualified)
    domains = {_domain_of(caller) for caller in callers}
    if len(domains) >= 3:
        return "CRITICAL_CORE"

    # [STEP 3] Chercher une référence de service ou du seed → niveau CORE
    if any(
        caller.split(".")[1:2] == ["services"] or caller.startswith("scripts.seed.")
        for caller in callers
    ):
        return "CORE"
    return "LEAF"


def weight_of(graph: CorpusGraph, qualified: str) -> int:
    """Poids d'un nœud : appels entrants + sortants dans le graphe résolu (R1)."""
    # [STEP 1] Sommer les degrés entrant et sortant → poids exact du nœud
    if qualified == SETTINGS_QUALIFIED:
        return len(graph.settings_readers)
    return len(called_by_of(graph, qualified)) + len(calls_of(graph, qualified))
