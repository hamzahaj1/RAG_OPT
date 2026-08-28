# [FILE] — app/scripts/seed.py
"""Idempotent seed of the development database (Milestone 9, SC-004).

Populates the five domains in graph order
(users → organizations → projects → tasks → comments) by get-or-create
on the D11 natural keys: ``users.email`` → ``organizations.name`` →
``projects(organization, name)`` → ``tasks(project, title)`` →
``comments(task, author, content)``. Two successive runs produce
exactly the same state — zero duplicates, zero errors. Creation
delegates to the domain services (D2 double layer preserved); the
constant dataset covers the 6 FK edges, the 2 roles, the 3 statuses,
the 3 priorities, assigned and unassigned tasks and ≥2 comments on a
same task. Executable: ``python -m app.scripts.seed`` (target
``make db-seed``).
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
    """Comments dataset entry — natural key (task, author, content)."""

    author_email: str
    content: str
    task_title: str


class SeedOrganization(TypedDict):
    """Organizations dataset entry — natural key ``name``."""

    name: str
    owner_email: str


class SeedProject(TypedDict):
    """Projects dataset entry — natural key (organization, name)."""

    description: str
    name: str
    organization_name: str


class SeedTask(TypedDict):
    """Tasks dataset entry — natural key (project, title)."""

    assignee_email: str | None
    description: str
    priority: str
    project_name: str
    status: str
    title: str


class SeedUser(TypedDict):
    """Users dataset entry — natural key ``email``."""

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
# tier: CORE
# weight: 2
# reads: comments
# mutates: none
# calls: comments.services.create_comment
# called_by: scripts.seed.seed_database
# [/RAG]
async def _ensure_comment(
    db: AsyncSession, author_id: int, data: SeedComment, task_id: int
) -> Comment:
    """Returns the comment of natural key (task, author, content), created if needed.

    Business rules:
    - the natural key is the full triplet (D11) — two identical
      contents from distinct authors or tasks remain two rows;
    - creation delegates to ``create_comment``: the service's 404
      checks preserved (D2 double layer).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    existing: Comment | None
    # ─────────────────────────────────────────

    # [STEP 1] Look up the natural key → the existing row is reused as is
    existing = await db.scalar(
        select(Comment).where(
            Comment.author_id == author_id,
            Comment.content == data["content"],
            Comment.task_id == task_id,
        )
    )
    if existing is not None:
        return existing

    # [STEP 2] Create through the domain service → domain invariants applied
    return await comments_services.create_comment(
        db,
        CommentCreate(author_id=author_id, content=data["content"], task_id=task_id),
    )


# [RAG]
# signature: _ensure_organization(db: AsyncSession, data: SeedOrganization,
#   owner_id: int) -> Organization
# tier: CORE
# weight: 2
# reads: organizations
# mutates: none
# calls: organizations.services.create_organization
# called_by: scripts.seed.seed_database
# [/RAG]
async def _ensure_organization(
    db: AsyncSession, data: SeedOrganization, owner_id: int
) -> Organization:
    """Returns the organization of natural key ``name``, created if needed.

    Business rules:
    - ``organizations.name`` is UNIQUE (D14): the lookup by name is
      deterministic;
    - creation delegates to ``create_organization``: the owner's 404
      check preserved (D2 double layer).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    existing: Organization | None
    # ─────────────────────────────────────────

    # [STEP 1] Look up the natural key → the existing row is reused as is
    existing = await db.scalar(select(Organization).where(Organization.name == data["name"]))
    if existing is not None:
        return existing

    # [STEP 2] Create through the domain service → domain invariants applied
    return await organizations_services.create_organization(
        db, OrganizationCreate(name=data["name"], owner_id=owner_id)
    )


# [RAG]
# signature: _ensure_project(db: AsyncSession, data: SeedProject, organization_id: int) -> Project
# tier: CORE
# weight: 2
# reads: projects
# mutates: none
# calls: projects.services.create_project
# called_by: scripts.seed.seed_database
# [/RAG]
async def _ensure_project(db: AsyncSession, data: SeedProject, organization_id: int) -> Project:
    """Returns the project of natural key (organization, name), created if needed.

    Business rules:
    - the composite uniqueness ``(organization_id, name)`` (D14) makes
      the lookup deterministic — the same name may exist elsewhere;
    - creation delegates to ``create_project``: the service's checks
      preserved (D2 double layer).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    existing: Project | None
    # ─────────────────────────────────────────

    # [STEP 1] Look up the natural key → the existing row is reused as is
    existing = await db.scalar(
        select(Project).where(
            Project.name == data["name"], Project.organization_id == organization_id
        )
    )
    if existing is not None:
        return existing

    # [STEP 2] Create through the domain service → domain invariants applied
    return await projects_services.create_project(
        db,
        ProjectCreate(
            description=data["description"], name=data["name"], organization_id=organization_id
        ),
    )


# [RAG]
# signature: _ensure_task(db: AsyncSession, assignee_id: int | None, data: SeedTask,
#   project_id: int) -> Task
# tier: CORE
# weight: 2
# reads: tasks
# mutates: none
# calls: tasks.services.create_task
# called_by: scripts.seed.seed_database
# [/RAG]
async def _ensure_task(
    db: AsyncSession, assignee_id: int | None, data: SeedTask, project_id: int
) -> Task:
    """Returns the task of natural key (project, title), created if needed.

    Business rules:
    - ``tasks.title`` carries no uniqueness constraint (D14): the
      get-or-create determinism rests on the constant dataset, which
      never repeats a (project, title) pair;
    - creation delegates to ``create_task``: the project's and
      assignee's 404 checks preserved (D2 double layer).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    existing: Task | None
    # ─────────────────────────────────────────

    # [STEP 1] Look up the natural key → the existing row is reused as is
    existing = await db.scalar(
        select(Task).where(Task.project_id == project_id, Task.title == data["title"])
    )
    if existing is not None:
        return existing

    # [STEP 2] Create through the domain service → domain invariants applied
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
# tier: CORE
# weight: 2
# reads: users
# mutates: none
# calls: users.services.create_user
# called_by: scripts.seed.seed_database
# [/RAG]
async def _ensure_user(db: AsyncSession, data: SeedUser) -> User:
    """Returns the user of natural key ``email``, created if needed.

    Business rules:
    - ``users.email`` is UNIQUE (FR-007): the lookup by email is
      deterministic;
    - creation delegates to ``create_user``: bcrypt password hashing
      preserved — an existing user is never re-hashed.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    existing: User | None
    # ─────────────────────────────────────────

    # [STEP 1] Look up the natural key → the existing row is reused as is
    existing = await db.scalar(select(User).where(User.email == data["email"]))
    if existing is not None:
        return existing

    # [STEP 2] Create through the domain service → domain invariants applied
    return await users_services.create_user(db, UserCreate.model_validate(data))


# [RAG]
# signature: main() -> None
# tier: LEAF
# weight: 1
# reads: none
# mutates: none
# calls: scripts.seed.run
# called_by: none
# [/RAG]
def main() -> None:
    """Synchronous entry point of ``python -m app.scripts.seed``.

    Invariant: re-runnable N times with no duplicate and no divergence
    (SC-004) — all the idempotence logic lives in ``seed_database``.
    """
    # [STEP 1] Start the asyncio loop → seed executed, resources released on exit
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())


# [RAG]
# signature: run() -> None
# tier: CORE
# weight: 3
# reads: none
# mutates: none
# calls: core.database.init_db_engine, scripts.seed.seed_database
# called_by: scripts.seed.main
# [/RAG]
async def run() -> None:
    """Runs the seed on the project database through the application engine.

    Invariants:
    - the engine comes from ``init_db_engine()`` and the session from
      ``async_session_factory`` — never a hand-built session;
    - the engine is disposed even when the seed fails.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    engine: AsyncEngine
    session: AsyncSession
    # ─────────────────────────────────────────

    # [STEP 1] Create the engine and bind the factory → sessions from the app engine
    engine = init_db_engine()
    async_session_factory.configure(bind=engine)

    # [STEP 2] Open a session and seed → same final state on every run
    try:
        async with async_session_factory() as session:
            await seed_database(session)
        logger.info("Seed applied: demo database populated.")
    finally:
        # [STEP 3] Dispose the engine → no residual connection
        await engine.dispose()


# [RAG]
# signature: seed_database(db: AsyncSession) -> None
# tier: CORE
# weight: 6
# reads: none
# mutates: none
# calls: scripts.seed._ensure_comment, scripts.seed._ensure_organization,
#   scripts.seed._ensure_project, scripts.seed._ensure_task, scripts.seed._ensure_user
# called_by: scripts.seed.run
# [/RAG]
async def seed_database(db: AsyncSession) -> None:
    """Seeds the five domains in graph order, by natural key.

    Business rules:
    - strict order users → organizations → projects → tasks → comments:
      each step resolves the next step's FKs by natural key (D11);
    - strict idempotence: every entity is looked up before being
      created — two successive runs produce exactly the same state;
    - the constant dataset covers the 6 FK edges, 2 roles, 3 statuses,
      3 priorities, assigned and unassigned tasks, ≥2 comments on a
      same task (Milestone 9 plan).
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

    # [STEP 1] Seed the users → users indexed by email for downstream FKs
    users = {}
    for user_data in SEED_USERS:
        users[user_data["email"]] = await _ensure_user(db, user_data)

    # [STEP 2] Seed the organizations → owner_id edge resolved by email
    organizations = {}
    for organization_data in SEED_ORGANIZATIONS:
        organizations[organization_data["name"]] = await _ensure_organization(
            db, organization_data, users[organization_data["owner_email"]].id
        )

    # [STEP 3] Seed the projects → organization_id edge resolved by name
    projects = {}
    for project_data in SEED_PROJECTS:
        projects[project_data["name"]] = await _ensure_project(
            db, project_data, organizations[project_data["organization_name"]].id
        )

    # [STEP 4] Seed the tasks → project_id and assignee_id (sometimes null) edges resolved
    tasks = {}
    for task_data in SEED_TASKS:
        assignee_email = task_data["assignee_email"]
        tasks[task_data["title"]] = await _ensure_task(
            db,
            users[assignee_email].id if assignee_email is not None else None,
            task_data,
            projects[task_data["project_name"]].id,
        )

    # [STEP 5] Seed the comments → task_id and author_id edges resolved
    for comment_data in SEED_COMMENTS:
        await _ensure_comment(
            db,
            users[comment_data["author_email"]].id,
            comment_data,
            tasks[comment_data["task_title"]].id,
        )


if __name__ == "__main__":
    main()
