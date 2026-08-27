# [FILE] — tests/unit/test_seed.py
"""Tests unitaires du jeu de données constant du seed — aucun accès DB.

Vérifient les préconditions structurelles de l'idempotence : chaque
référence interne du jeu se résout par clé naturelle (D11), aucune clé
naturelle n'est dupliquée (condition du get-or-create déterministe), et
la couverture obligatoire du plan Jalon 9 est atteinte (2 rôles,
3 statuts, 3 priorités, tâches assignées et non assignées,
≥2 commentaires sur une même tâche, volumes exacts).
"""

# ─── IMPORTS ───
from collections import Counter

from app.scripts.seed import (
    SEED_COMMENTS,
    SEED_ORGANIZATIONS,
    SEED_PROJECTS,
    SEED_TASKS,
    SEED_USERS,
)

# ──────────────

# [CODE_START]


def test_seed_dataset_covers_enums_and_roles() -> None:
    """Le jeu couvre les deux rôles, les trois statuts, les trois priorités.

    C'est la couverture d'ensembles fermés exigée par le plan Jalon 9 :
    un pipeline RAG indexant le seed doit rencontrer chaque valeur.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    priorities: set[str]
    roles: set[str]
    statuses: set[str]
    # ─────────────────────────────────────────

    # [STEP 1] Collecter les valeurs d'enum du jeu → chaque ensemble fermé est complet
    priorities = {task["priority"] for task in SEED_TASKS}
    roles = {user["role"] for user in SEED_USERS}
    statuses = {task["status"] for task in SEED_TASKS}
    assert priorities == {"high", "low", "medium"}
    assert roles == {"admin", "member"}
    assert statuses == {"done", "in_progress", "todo"}


def test_seed_dataset_exercises_optional_and_nested_edges() -> None:
    """Le jeu exerce l'assignation optionnelle et l'imbrication des commentaires.

    Couverture exigée : au moins une tâche assignée, au moins une tâche
    libre, au moins deux commentaires sur une même tâche, et un projet
    multi-tâches — les volumes du plan (5, 2, 4, 12, 8) sont exacts.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    comments_per_task: Counter[str]
    tasks_per_project: Counter[str]
    # ─────────────────────────────────────────

    # [STEP 1] Compter les volumes → conformes au plan Jalon 9
    assert len(SEED_USERS) == 5
    assert len(SEED_ORGANIZATIONS) == 2
    assert len(SEED_PROJECTS) == 4
    assert len(SEED_TASKS) == 12
    assert len(SEED_COMMENTS) == 8

    # [STEP 2] Vérifier l'assignation optionnelle → les deux cas présents dans le jeu
    assert any(task["assignee_email"] is not None for task in SEED_TASKS)
    assert any(task["assignee_email"] is None for task in SEED_TASKS)

    # [STEP 3] Vérifier l'imbrication → tâche multi-commentée et projet multi-tâches
    comments_per_task = Counter(comment["task_title"] for comment in SEED_COMMENTS)
    tasks_per_project = Counter(task["project_name"] for task in SEED_TASKS)
    assert max(comments_per_task.values()) >= 2
    assert max(tasks_per_project.values()) >= 2


def test_seed_dataset_natural_keys_are_unique() -> None:
    """Aucune clé naturelle n'est dupliquée dans le jeu de données.

    Condition du get-or-create déterministe (D11) : emails, noms
    d'organisations et de projets globalement uniques (la résolution des
    FK se fait par nom seul), couples (project, title) et triplets
    (task, author, content) sans doublon.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    comment_keys: list[tuple[str, str, str]]
    emails: list[str]
    organization_names: list[str]
    project_names: list[str]
    task_keys: list[tuple[str, str]]
    # ─────────────────────────────────────────

    # [STEP 1] Collecter chaque clé naturelle → listes ordonnées, doublons visibles
    comment_keys = [
        (comment["task_title"], comment["author_email"], comment["content"])
        for comment in SEED_COMMENTS
    ]
    emails = [user["email"] for user in SEED_USERS]
    organization_names = [organization["name"] for organization in SEED_ORGANIZATIONS]
    project_names = [project["name"] for project in SEED_PROJECTS]
    task_keys = [(task["project_name"], task["title"]) for task in SEED_TASKS]

    # [STEP 2] Comparer aux ensembles → aucune clé perdue par déduplication
    assert len(set(comment_keys)) == len(comment_keys)
    assert len(set(emails)) == len(emails)
    assert len(set(organization_names)) == len(organization_names)
    assert len(set(project_names)) == len(project_names)
    assert len(set(task_keys)) == len(task_keys)


def test_seed_dataset_references_resolve() -> None:
    """Chaque référence inter-domaines du jeu pointe une clé naturelle existante.

    Les 6 arêtes FK du graphe sont résolues avant toute écriture : owner
    et auteurs par email, projets par nom d'organisation, tâches par nom
    de projet, commentaires par titre de tâche, assignés par email ou
    ``None`` explicite.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    emails: set[str]
    organization_names: set[str]
    project_names: set[str]
    task_titles: set[str]
    # ─────────────────────────────────────────

    # [STEP 1] Indexer les clés naturelles amont → cibles de résolution disponibles
    emails = {user["email"] for user in SEED_USERS}
    organization_names = {organization["name"] for organization in SEED_ORGANIZATIONS}
    project_names = {project["name"] for project in SEED_PROJECTS}
    task_titles = {task["title"] for task in SEED_TASKS}

    # [STEP 2] Vérifier chaque arête du jeu → aucune référence orpheline possible
    assert all(org["owner_email"] in emails for org in SEED_ORGANIZATIONS)
    assert all(project["organization_name"] in organization_names for project in SEED_PROJECTS)
    assert all(task["project_name"] in project_names for task in SEED_TASKS)
    assert all(
        task["assignee_email"] is None or task["assignee_email"] in emails for task in SEED_TASKS
    )
    assert all(comment["author_email"] in emails for comment in SEED_COMMENTS)
    assert all(comment["task_title"] in task_titles for comment in SEED_COMMENTS)
