# [FILE] — app/scripts/seed.py
"""Seed idempotent de la base de développement (Jalon 9, SC-004).

Peuple les cinq domaines dans l'ordre du graphe
(users → organizations → projects → tasks → comments) par get-or-create
sur les clés naturelles de D11 : ``users.email`` → ``organizations.name``
→ ``projects(organization, name)`` → ``tasks(project, title)`` →
``comments(task, author, content)``. Deux exécutions successives
produisent exactement le même état — zéro doublon, zéro erreur. La
création délègue aux services de domaines (double couche D2 conservée) ;
le jeu de données constant couvre les 6 arêtes FK, les 2 rôles, les
3 statuts, les 3 priorités, des tâches assignées et non assignées et
≥2 commentaires sur une même tâche. Exécutable :
``python -m app.scripts.seed`` (cible ``make db-seed``).
"""

# ─── IMPORTS ───
import asyncio
import logging
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.database import async_session_factory, init_db_engine
from app.domains.comments import services as comments_services
from app.domains.comments.models import Comment
from app.domains.comments.schemas import CommentCreate
from app.domains.organizations import services as organizations_services
from app.domains.organizations.models import Organization
from app.domains.organizations.schemas import OrganizationCreate
from app.domains.projects import services as projects_services
from app.domains.projects.models import Project
from app.domains.projects.schemas import ProjectCreate
from app.domains.tasks import services as tasks_services
from app.domains.tasks.models import Task, TaskPriority, TaskStatus
from app.domains.tasks.schemas import TaskCreate
from app.domains.users import services as users_services
from app.domains.users.models import User
from app.domains.users.schemas import UserCreate

# ──────────────

# [CODE_START]

logger = logging.getLogger(__name__)


class SeedComment(TypedDict):
    """Entrée du jeu de données commentaires — clé naturelle (task, author, content)."""

    author_email: str
    content: str
    task_title: str


class SeedOrganization(TypedDict):
    """Entrée du jeu de données organisations — clé naturelle ``name``."""

    name: str
    owner_email: str


class SeedProject(TypedDict):
    """Entrée du jeu de données projets — clé naturelle (organization, name)."""

    description: str
    name: str
    organization_name: str


class SeedTask(TypedDict):
    """Entrée du jeu de données tâches — clé naturelle (project, title)."""

    assignee_email: str | None
    description: str
    priority: str
    project_name: str
    status: str
    title: str


class SeedUser(TypedDict):
    """Entrée du jeu de données utilisateurs — clé naturelle ``email``."""

    email: str
    full_name: str
    password: str
    role: str


SEED_COMMENTS: tuple[SeedComment, ...] = (
    {
        "author_email": "ada@alpha-scope.dev",
        "content": "Header layout matches the V3 standard.",
        "task_title": "Parse AST headers",
    },
    {
        "author_email": "carol@alpha-scope.dev",
        "content": "Weight computation verified on the users domain.",
        "task_title": "Parse AST headers",
    },
    {
        "author_email": "dave@alpha-scope.dev",
        "content": "Chunk boundaries align with STEP markers.",
        "task_title": "Chunk service files",
    },
    {
        "author_email": "erin@alpha-scope.dev",
        "content": "Embedding model pinned for reproducibility.",
        "task_title": "Embed code chunks",
    },
    {
        "author_email": "bob@alpha-scope.dev",
        "content": "Import resolver handles module aliases.",
        "task_title": "Build call graph",
    },
    {
        "author_email": "carol@alpha-scope.dev",
        "content": "Twenty percent overlap wins on recall.",
        "task_title": "Tune chunk overlap",
    },
    {
        "author_email": "ada@alpha-scope.dev",
        "content": "Sandbox network egress is disabled.",
        "task_title": "Isolate test sandbox",
    },
    {
        "author_email": "erin@alpha-scope.dev",
        "content": "Sidebar mirrors the domain list.",
        "task_title": "Draft dashboard layout",
    },
)

SEED_ORGANIZATIONS: tuple[SeedOrganization, ...] = (
    {"name": "Alpha Scope Labs", "owner_email": "ada@alpha-scope.dev"},
    {"name": "Beta Rag Guild", "owner_email": "bob@alpha-scope.dev"},
)

SEED_PROJECTS: tuple[SeedProject, ...] = (
    {
        "description": "AST parsing and chunk extraction for the RAG corpus.",
        "name": "Ingestion Pipeline",
        "organization_name": "Alpha Scope Labs",
    },
    {
        "description": "Code graph construction and structural retrieval.",
        "name": "Retrieval Graph",
        "organization_name": "Alpha Scope Labs",
    },
    {
        "description": "Isolated execution environment for the agentic loop.",
        "name": "Sandbox Runner",
        "organization_name": "Beta Rag Guild",
    },
    {
        "description": "Operator dashboard over the generation metrics.",
        "name": "Web Console",
        "organization_name": "Beta Rag Guild",
    },
)

SEED_TASKS: tuple[SeedTask, ...] = (
    {
        "assignee_email": "carol@alpha-scope.dev",
        "description": "Extract the [RAG] headers from every service file.",
        "priority": "high",
        "project_name": "Ingestion Pipeline",
        "status": "todo",
        "title": "Parse AST headers",
    },
    {
        "assignee_email": "dave@alpha-scope.dev",
        "description": "Split services on STEP markers into stable chunks.",
        "priority": "high",
        "project_name": "Ingestion Pipeline",
        "status": "in_progress",
        "title": "Chunk service files",
    },
    {
        "assignee_email": None,
        "description": "Vectorize the annotated chunks for retrieval.",
        "priority": "medium",
        "project_name": "Ingestion Pipeline",
        "status": "todo",
        "title": "Embed code chunks",
    },
    {
        "assignee_email": "ada@alpha-scope.dev",
        "description": "Emit TOPOLOGY.yaml from the resolved call graph.",
        "priority": "low",
        "project_name": "Ingestion Pipeline",
        "status": "done",
        "title": "Write topology YAML",
    },
    {
        "assignee_email": "erin@alpha-scope.dev",
        "description": "Load the embeddings into the vector store.",
        "priority": "medium",
        "project_name": "Ingestion Pipeline",
        "status": "in_progress",
        "title": "Index vector store",
    },
    {
        "assignee_email": None,
        "description": "Resolve imports and aliases across domains.",
        "priority": "low",
        "project_name": "Retrieval Graph",
        "status": "todo",
        "title": "Build call graph",
    },
    {
        "assignee_email": "carol@alpha-scope.dev",
        "description": "Score retrieved chunks against cross-domain questions.",
        "priority": "low",
        "project_name": "Retrieval Graph",
        "status": "in_progress",
        "title": "Rank cross-domain hits",
    },
    {
        "assignee_email": "dave@alpha-scope.dev",
        "description": "Measure recall against chunk overlap ratios.",
        "priority": "medium",
        "project_name": "Retrieval Graph",
        "status": "done",
        "title": "Tune chunk overlap",
    },
    {
        "assignee_email": "erin@alpha-scope.dev",
        "description": "Deny network egress inside the execution sandbox.",
        "priority": "high",
        "project_name": "Sandbox Runner",
        "status": "done",
        "title": "Isolate test sandbox",
    },
    {
        "assignee_email": None,
        "description": "Re-run failed generations with captured inputs.",
        "priority": "medium",
        "project_name": "Sandbox Runner",
        "status": "todo",
        "title": "Replay failing runs",
    },
    {
        "assignee_email": "bob@alpha-scope.dev",
        "description": "Sketch the metrics dashboard information layout.",
        "priority": "high",
        "project_name": "Web Console",
        "status": "in_progress",
        "title": "Draft dashboard layout",
    },
    {
        "assignee_email": None,
        "description": "Connect the query panel to the retrieval API.",
        "priority": "low",
        "project_name": "Web Console",
        "status": "done",
        "title": "Wire query panel",
    },
)

SEED_USERS: tuple[SeedUser, ...] = (
    {
        "email": "ada@alpha-scope.dev",
        "full_name": "Ada Admin",
        "password": "seed-ada-pw",
        "role": "admin",
    },
    {
        "email": "bob@alpha-scope.dev",
        "full_name": "Bob Builder",
        "password": "seed-bob-pw",
        "role": "member",
    },
    {
        "email": "carol@alpha-scope.dev",
        "full_name": "Carol Curator",
        "password": "seed-carol-pw",
        "role": "member",
    },
    {
        "email": "dave@alpha-scope.dev",
        "full_name": "Dave Drafter",
        "password": "seed-dave-pw",
        "role": "member",
    },
    {
        "email": "erin@alpha-scope.dev",
        "full_name": "Erin Explorer",
        "password": "seed-erin-pw",
        "role": "admin",
    },
)


# [RAG]
# signature: _ensure_comment(db: AsyncSession, author_id: int, data: SeedComment,
#   task_id: int) -> Comment
# weight: 2
# tier: CORE
# calls: comments.services.create_comment
# called_by: scripts.seed.seed_database
# reads: comments
# mutates: none
# [/RAG]
async def _ensure_comment(
    db: AsyncSession, author_id: int, data: SeedComment, task_id: int
) -> Comment:
    """Retourne le commentaire de clé naturelle (task, author, content), créé au besoin.

    Règles métier :
    - la clé naturelle est le triplet complet (D11) — deux contenus
      identiques d'auteurs ou de tâches distincts restent deux lignes ;
    - la création délègue à ``create_comment`` : vérifications 404 du
      service conservées (double couche D2).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    existing: Comment | None
    # ─────────────────────────────────────────

    # [STEP 1] Chercher la clé naturelle → l'existant est réutilisé tel quel
    existing = await db.scalar(
        select(Comment).where(
            Comment.author_id == author_id,
            Comment.content == data["content"],
            Comment.task_id == task_id,
        )
    )
    if existing is not None:
        return existing

    # [STEP 2] Créer via le service du domaine → invariants du domaine appliqués
    return await comments_services.create_comment(
        db,
        CommentCreate(author_id=author_id, content=data["content"], task_id=task_id),
    )


# [RAG]
# signature: _ensure_organization(db: AsyncSession, data: SeedOrganization,
#   owner_id: int) -> Organization
# weight: 2
# tier: CORE
# calls: organizations.services.create_organization
# called_by: scripts.seed.seed_database
# reads: organizations
# mutates: none
# [/RAG]
async def _ensure_organization(
    db: AsyncSession, data: SeedOrganization, owner_id: int
) -> Organization:
    """Retourne l'organisation de clé naturelle ``name``, créée au besoin.

    Règles métier :
    - ``organizations.name`` est UNIQUE (D14) : la recherche par nom est
      déterministe ;
    - la création délègue à ``create_organization`` : vérification 404 du
      propriétaire conservée (double couche D2).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    existing: Organization | None
    # ─────────────────────────────────────────

    # [STEP 1] Chercher la clé naturelle → l'existant est réutilisé tel quel
    existing = await db.scalar(select(Organization).where(Organization.name == data["name"]))
    if existing is not None:
        return existing

    # [STEP 2] Créer via le service du domaine → invariants du domaine appliqués
    return await organizations_services.create_organization(
        db, OrganizationCreate(name=data["name"], owner_id=owner_id)
    )


# [RAG]
# signature: _ensure_project(db: AsyncSession, data: SeedProject, organization_id: int) -> Project
# weight: 2
# tier: CORE
# calls: projects.services.create_project
# called_by: scripts.seed.seed_database
# reads: projects
# mutates: none
# [/RAG]
async def _ensure_project(db: AsyncSession, data: SeedProject, organization_id: int) -> Project:
    """Retourne le projet de clé naturelle (organization, name), créé au besoin.

    Règles métier :
    - l'unicité composée ``(organization_id, name)`` (D14) rend la
      recherche déterministe — le même nom peut exister ailleurs ;
    - la création délègue à ``create_project`` : vérifications du service
      conservées (double couche D2).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    existing: Project | None
    # ─────────────────────────────────────────

    # [STEP 1] Chercher la clé naturelle → l'existant est réutilisé tel quel
    existing = await db.scalar(
        select(Project).where(
            Project.name == data["name"], Project.organization_id == organization_id
        )
    )
    if existing is not None:
        return existing

    # [STEP 2] Créer via le service du domaine → invariants du domaine appliqués
    return await projects_services.create_project(
        db,
        ProjectCreate(
            description=data["description"], name=data["name"], organization_id=organization_id
        ),
    )


# [RAG]
# signature: _ensure_task(db: AsyncSession, assignee_id: int | None, data: SeedTask,
#   project_id: int) -> Task
# weight: 2
# tier: CORE
# calls: tasks.services.create_task
# called_by: scripts.seed.seed_database
# reads: tasks
# mutates: none
# [/RAG]
async def _ensure_task(
    db: AsyncSession, assignee_id: int | None, data: SeedTask, project_id: int
) -> Task:
    """Retourne la tâche de clé naturelle (project, title), créée au besoin.

    Règles métier :
    - ``tasks.title`` ne porte aucune contrainte d'unicité (D14) : la
      détermination du get-or-create repose sur le jeu de données constant,
      qui ne répète jamais un couple (project, title) ;
    - la création délègue à ``create_task`` : vérifications 404 du projet
      et de l'assigné conservées (double couche D2).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    existing: Task | None
    # ─────────────────────────────────────────

    # [STEP 1] Chercher la clé naturelle → l'existant est réutilisé tel quel
    existing = await db.scalar(
        select(Task).where(Task.project_id == project_id, Task.title == data["title"])
    )
    if existing is not None:
        return existing

    # [STEP 2] Créer via le service du domaine → invariants du domaine appliqués
    return await tasks_services.create_task(
        db,
        TaskCreate(
            assignee_id=assignee_id,
            description=data["description"],
            priority=TaskPriority(data["priority"]),
            project_id=project_id,
            status=TaskStatus(data["status"]),
            title=data["title"],
        ),
    )


# [RAG]
# signature: _ensure_user(db: AsyncSession, data: SeedUser) -> User
# weight: 2
# tier: CORE
# calls: users.services.create_user
# called_by: scripts.seed.seed_database
# reads: users
# mutates: none
# [/RAG]
async def _ensure_user(db: AsyncSession, data: SeedUser) -> User:
    """Retourne l'utilisateur de clé naturelle ``email``, créé au besoin.

    Règles métier :
    - ``users.email`` est UNIQUE (FR-007) : la recherche par email est
      déterministe ;
    - la création délègue à ``create_user`` : hachage bcrypt du mot de
      passe conservé — un utilisateur existant n'est jamais re-haché.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    existing: User | None
    # ─────────────────────────────────────────

    # [STEP 1] Chercher la clé naturelle → l'existant est réutilisé tel quel
    existing = await db.scalar(select(User).where(User.email == data["email"]))
    if existing is not None:
        return existing

    # [STEP 2] Créer via le service du domaine → invariants du domaine appliqués
    return await users_services.create_user(db, UserCreate.model_validate(data))


# [RAG]
# signature: main() -> None
# weight: 1
# tier: LEAF
# calls: scripts.seed.run
# called_by: none
# reads: none
# mutates: none
# [/RAG]
def main() -> None:
    """Point d'entrée synchrone de ``python -m app.scripts.seed``.

    Invariant : relançable N fois sans doublon ni divergence (SC-004) —
    toute la logique d'idempotence vit dans ``seed_database``.
    """
    # [STEP 1] Démarrer la boucle asyncio → seed exécuté, ressources libérées en sortie
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())


# [RAG]
# signature: run() -> None
# weight: 3
# tier: CORE
# calls: core.database.init_db_engine, scripts.seed.seed_database
# called_by: scripts.seed.main
# reads: none
# mutates: none
# [/RAG]
async def run() -> None:
    """Exécute le seed sur la base du projet via le moteur applicatif.

    Invariants :
    - le moteur vient de ``init_db_engine()`` et la session de
      ``async_session_factory`` — jamais de session construite à la main ;
    - le moteur est libéré même en cas d'échec du seed.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    engine: AsyncEngine
    session: AsyncSession
    # ─────────────────────────────────────────

    # [STEP 1] Créer le moteur et lier la factory → sessions du moteur applicatif
    engine = init_db_engine()
    async_session_factory.configure(bind=engine)

    # [STEP 2] Ouvrir une session et semer → état final identique à chaque exécution
    try:
        async with async_session_factory() as session:
            await seed_database(session)
        logger.info("Seed appliqué : base de démonstration peuplée.")
    finally:
        # [STEP 3] Libérer le moteur → aucune connexion résiduelle
        await engine.dispose()


# [RAG]
# signature: seed_database(db: AsyncSession) -> None
# weight: 6
# tier: CORE
# calls: scripts.seed._ensure_comment, scripts.seed._ensure_organization,
#   scripts.seed._ensure_project, scripts.seed._ensure_task, scripts.seed._ensure_user
# called_by: scripts.seed.run
# reads: none
# mutates: none
# [/RAG]
async def seed_database(db: AsyncSession) -> None:
    """Sème les cinq domaines dans l'ordre du graphe, par clé naturelle.

    Règles métier :
    - ordre strict users → organizations → projects → tasks → comments :
      chaque étape résout les FK de la suivante par clé naturelle (D11) ;
    - idempotence stricte : chaque entité est cherchée avant d'être créée —
      deux exécutions successives produisent exactement le même état ;
    - le jeu constant couvre les 6 arêtes FK, 2 rôles, 3 statuts,
      3 priorités, tâches assignées et non assignées, ≥2 commentaires sur
      une même tâche (plan Jalon 9).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    assignee_email: str | None
    comment_data: SeedComment
    organization_data: SeedOrganization
    organizations: dict[str, Organization]
    project_data: SeedProject
    projects: dict[str, Project]
    task_data: SeedTask
    tasks: dict[str, Task]
    user_data: SeedUser
    users: dict[str, User]
    # ─────────────────────────────────────────

    # [STEP 1] Semer les utilisateurs → users indexés par email pour les FK aval
    users = {}
    for user_data in SEED_USERS:
        users[user_data["email"]] = await _ensure_user(db, user_data)

    # [STEP 2] Semer les organisations → arête owner_id résolue par email
    organizations = {}
    for organization_data in SEED_ORGANIZATIONS:
        organizations[organization_data["name"]] = await _ensure_organization(
            db, organization_data, users[organization_data["owner_email"]].id
        )

    # [STEP 3] Semer les projets → arête organization_id résolue par nom
    projects = {}
    for project_data in SEED_PROJECTS:
        projects[project_data["name"]] = await _ensure_project(
            db, project_data, organizations[project_data["organization_name"]].id
        )

    # [STEP 4] Semer les tâches → arêtes project_id et assignee_id (parfois nulle) résolues
    tasks = {}
    for task_data in SEED_TASKS:
        assignee_email = task_data["assignee_email"]
        tasks[task_data["title"]] = await _ensure_task(
            db,
            users[assignee_email].id if assignee_email is not None else None,
            task_data,
            projects[task_data["project_name"]].id,
        )

    # [STEP 5] Semer les commentaires → arêtes task_id et author_id résolues
    for comment_data in SEED_COMMENTS:
        await _ensure_comment(
            db,
            users[comment_data["author_email"]].id,
            comment_data,
            tasks[comment_data["task_title"]].id,
        )


if __name__ == "__main__":
    main()
