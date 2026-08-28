# [FILE] — app/main.py
"""FastAPI application assembly and database lifecycle.

Single entry point of the backend: domain routers (Phase 2) are mounted
in ``create_app``, nowhere else. The schema is synchronized at startup
for development; Alembic remains the reference tool for migrations
(Milestone 3).
"""

# ─── IMPORTS ───
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import settings
from app.core.database import Base, async_session_factory, init_db_engine
from app.domains.comments.router import router as comments_router
from app.domains.organizations.router import router as organizations_router
from app.domains.projects.router import router as projects_router
from app.domains.tasks.router import router as tasks_router
from app.domains.users.router import router as users_router

# ──────────────

# [CODE_START]

logger = logging.getLogger(__name__)


# [RAG]
# signature: create_app() -> FastAPI
# tier: LEAF
# weight: 1
# reads: settings
# mutates: none
# calls: main.lifespan
# called_by: none
# [/RAG]
def create_app() -> FastAPI:
    """Builds the complete FastAPI application.

    Rules:
    - the DB lifecycle goes exclusively through ``lifespan``;
    - each domain (Phase 2) mounts its router here, nowhere else.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    app: FastAPI
    # ─────────────────────────────────────────

    # [STEP 1] Instantiate FastAPI with the lifespan → DB lifecycle wired
    app = FastAPI(
        debug=settings.debug,
        lifespan=lifespan,
        title="Alpha-Scope RAG",
        version="0.1.0",
    )

    # [STEP 2] Mount the domain routers → /api/v1 endpoints active
    app.include_router(comments_router, prefix="/api/v1")
    app.include_router(organizations_router, prefix="/api/v1")
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(tasks_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")

    # [STEP 3] Expose the health probe → the app is checkable without touching the DB
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Liveness probe: never touches the database, always responds."""
        return {"status": "ok"}

    return app


# [RAG]
# signature: lifespan(app: FastAPI) -> AsyncIterator[None]
# tier: LEAF
# weight: 2
# reads: none
# mutates: none
# calls: core.database.init_db_engine
# called_by: main.create_app
# [/RAG]
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Clean startup and shutdown of DB resources.

    Invariants:
    - the session factory is bound to the engine before the first
      request;
    - the engine is disposed at shutdown, no connection leaks.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    engine: AsyncEngine
    # ─────────────────────────────────────────

    # [STEP 1] Create the async engine → DSN resolved from settings
    engine = init_db_engine()

    # [STEP 2] Bind the session factory → get_db delivers sessions from this engine
    async_session_factory.configure(bind=engine)

    # [STEP 3] Synchronize the schema (dev only) → model tables present
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    logger.info("Database ready.")

    yield

    # [STEP 4] Dispose the engine → all connections closed
    await engine.dispose()
    logger.info("Database engine disposed.")


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
