# [FILE] — tests/integration/test_seed_idempotence.py
"""Tests d'intégration du seed — idempotence contre PostgreSQL réel (SC-004).

Exécutent ``seed_database`` sur la base de test via la session directe
(``db_session``) : une première passe vérifie la couverture du graphe
(volumes exacts, 6 arêtes FK exercées, enums complets, tâche
multi-commentée) ; une passe double vérifie l'idempotence stricte —
comptes de lignes et ensembles de clés naturelles strictement identiques
entre les deux exécutions, zéro doublon, zéro erreur.
"""

# ─── IMPORTS ───
from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.comments.models import Comment
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.tasks.models import Task
from app.domains.users.models import User
from app.scripts.seed import seed_database

# ──────────────

# [CODE_START]


async def _snapshot(db: AsyncSession) -> dict[str, object]:
    """Photographie l'état seedé : comptes de lignes et clés naturelles (D11).

    Invariant : deux états identiques produisent deux photographies
    égales — la comparaison d'égalité suffit au test d'idempotence.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    comments: list[Comment]
    organizations: list[Organization]
    projects: list[Project]
    tasks: list[Task]
    users: list[User]
    # ─────────────────────────────────────────

    # [STEP 1] Charger les cinq tables → état complet en mémoire
    comments = list((await db.scalars(select(Comment))).all())
    organizations = list((await db.scalars(select(Organization))).all())
    projects = list((await db.scalars(select(Project))).all())
    tasks = list((await db.scalars(select(Task))).all())
    users = list((await db.scalars(select(User))).all())

    # [STEP 2] Réduire aux comptes et clés naturelles → photographie comparable
    return {
        "comment_keys": {(c.task_id, c.author_id, c.content) for c in comments},
        "counts": (len(users), len(organizations), len(projects), len(tasks), len(comments)),
        "emails": {user.email for user in users},
        "organization_names": {organization.name for organization in organizations},
        "project_keys": {(project.organization_id, project.name) for project in projects},
        "task_keys": {(task.project_id, task.title) for task in tasks},
    }


async def test_seed_covers_graph_and_enums(db_session: AsyncSession) -> None:
    """Une exécution du seed pose les volumes du plan et exerce tout le graphe.

    Couverture vérifiée en base : volumes exacts (5, 2, 4, 12, 8), les
    trois statuts et trois priorités présents, tâches assignées et non
    assignées, au moins une tâche portant deux commentaires — les 6 arêtes
    FK sont matérialisées par les lignes elles-mêmes (colonnes NOT NULL).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    comments_per_task: Counter[int]
    snapshot: dict[str, object]
    tasks: list[Task]
    # ─────────────────────────────────────────

    # [STEP 1] Semer une fois puis photographier → volumes exacts du plan
    await seed_database(db_session)
    snapshot = await _snapshot(db_session)
    assert snapshot["counts"] == (5, 2, 4, 12, 8)

    # [STEP 2] Inspecter les tâches → enums complets, assignation optionnelle exercée
    tasks = list((await db_session.scalars(select(Task))).all())
    assert {task.priority for task in tasks} == {"high", "low", "medium"}
    assert {task.status for task in tasks} == {"done", "in_progress", "todo"}
    assert any(task.assignee_id is not None for task in tasks)
    assert any(task.assignee_id is None for task in tasks)

    # [STEP 3] Compter les commentaires par tâche → imbrication multi-commentaire posée
    comments_per_task = Counter(
        comment.task_id for comment in (await db_session.scalars(select(Comment))).all()
    )
    assert max(comments_per_task.values()) >= 2


async def test_seed_twice_produces_identical_state(db_session: AsyncSession) -> None:
    """Deux exécutions successives produisent exactement le même état (SC-004).

    Idempotence stricte : la seconde passe ne crée aucune ligne, ne lève
    aucune erreur et laisse comptes et clés naturelles inchangés — le
    get-or-create par clé naturelle (D11) absorbe intégralement le rejeu.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    first: dict[str, object]
    second: dict[str, object]
    # ─────────────────────────────────────────

    # [STEP 1] Semer une première fois → état de référence photographié
    await seed_database(db_session)
    first = await _snapshot(db_session)

    # [STEP 2] Semer une seconde fois → aucune erreur levée par le rejeu
    await seed_database(db_session)
    second = await _snapshot(db_session)

    # [STEP 3] Comparer les photographies → état final strictement identique
    assert first == second
    assert first["counts"] == (5, 2, 4, 12, 8)
