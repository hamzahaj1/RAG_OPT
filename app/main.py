# [FILE] — app/main.py
"""Assemblage de l'application FastAPI et cycle de vie de la base.

Point d'entrée unique du backend : les routeurs de domaines (Phase 2) se
montent dans ``create_app``, nulle part ailleurs. Le schéma est synchronisé
au démarrage pour le développement ; Alembic reste l'outil de référence
pour les migrations (Jalon 3).
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
# weight: 1
# tier: LEAF
# calls: main.lifespan
# called_by: none
# reads: settings
# mutates: none
# [/RAG]
def create_app() -> FastAPI:
    """Construit l'application FastAPI complète.

    Règles :
    - le cycle de vie DB passe exclusivement par ``lifespan`` ;
    - chaque domaine (Phase 2) monte son routeur ici, nulle part ailleurs.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    app: FastAPI
    # ─────────────────────────────────────────

    # [STEP 1] Instancier FastAPI avec le lifespan → cycle de vie DB branché
    app = FastAPI(
        debug=settings.debug,
        lifespan=lifespan,
        title="Alpha-Scope RAG",
        version="0.1.0",
    )

    # [STEP 2] Monter les routeurs de domaines → endpoints /api/v1 actifs
    app.include_router(comments_router, prefix="/api/v1")
    app.include_router(organizations_router, prefix="/api/v1")
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(tasks_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")

    # [STEP 3] Exposer la sonde de santé → l'app est vérifiable sans toucher la DB
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Sonde de vivacité : ne touche pas la base, répond toujours."""
        return {"status": "ok"}

    return app


# [RAG]
# signature: lifespan(app: FastAPI) -> AsyncIterator[None]
# weight: 2
# tier: LEAF
# calls: core.database.init_db_engine
# called_by: main.create_app
# reads: none
# mutates: none
# [/RAG]
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Démarrage et arrêt propres des ressources DB.

    Invariants :
    - la factory de sessions est liée au moteur avant la première requête ;
    - le moteur est libéré à l'arrêt, aucune connexion ne fuit.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    engine: AsyncEngine
    # ─────────────────────────────────────────

    # [STEP 1] Créer le moteur async → DSN résolu depuis settings
    engine = init_db_engine()

    # [STEP 2] Lier la factory de sessions → get_db délivre des sessions de ce moteur
    async_session_factory.configure(bind=engine)

    # [STEP 3] Synchroniser le schéma (dev uniquement) → tables des modèles présentes
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    logger.info("Base de données prête.")

    yield

    # [STEP 4] Libérer le moteur → toutes les connexions fermées
    await engine.dispose()
    logger.info("Moteur de base de données libéré.")


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
