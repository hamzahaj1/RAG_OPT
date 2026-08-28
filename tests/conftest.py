# [FILE] — tests/conftest.py
"""Fixtures partagées de la suite de tests (D10).

La base dédiée ``alpha_scope_test`` vit sur le même PostgreSQL que le
développement : son DSN est dérivé de ``settings.database_url`` en
remplaçant le nom de base — aucune variable d'environnement
supplémentaire. Le schéma est posé une fois par session (``drop_all`` +
``create_all`` de ``Base.metadata``) ; le nettoyage entre tests (TRUNCATE
autouse) vit dans ``tests/integration/conftest.py`` afin que
``tests/unit`` reste exécutable sans PostgreSQL.
"""

# ─── IMPORTS ───
from collections.abc import AsyncGenerator, AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import create_app

# ──────────────

# [CODE_START]

TEST_DATABASE_NAME = "alpha_scope_test"


def _replace_database_name(database_name: str, url: str) -> str:
    """Substitue le nom de base d'un DSN PostgreSQL.

    Invariant : le DSN du projet se termine par ``/<nom_de_base>`` sans
    paramètres de requête — la substitution par découpe est déterministe.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    base_url: str
    # ─────────────────────────────────

    # [STEP 1] Découper sur le dernier « / » → autorité conservée, base remplacée
    base_url = url.rsplit("/", 1)[0]
    return f"{base_url}/{database_name}"


async def _create_database_if_missing() -> None:
    """Crée la base ``alpha_scope_test`` si elle n'existe pas encore.

    Cas limites :
    - ``CREATE DATABASE`` est interdit en transaction → connexion
      AUTOCOMMIT sur la base d'administration ``postgres`` ;
    - la création n'est tentée que si la base est réellement absente.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    admin_engine: AsyncEngine
    existing: int | None
    # ─────────────────────────────────

    # [STEP 1] Ouvrir un moteur AUTOCOMMIT sur la base postgres → DDL hors transaction
    admin_engine = create_async_engine(
        _replace_database_name("postgres", settings.database_url),
        isolation_level="AUTOCOMMIT",
    )

    # [STEP 2] Créer la base si absente → alpha_scope_test disponible
    async with admin_engine.connect() as connection:
        existing = await connection.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": TEST_DATABASE_NAME},
        )
        if existing is None:
            await connection.execute(text(f'CREATE DATABASE "{TEST_DATABASE_NAME}"'))

    # [STEP 3] Libérer le moteur d'administration → aucune connexion résiduelle
    await admin_engine.dispose()


@pytest.fixture
async def client(db_engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    """Client HTTP ASGI sur ``create_app()``, sessions DB redirigées vers le test.

    Invariants :
    - le lifespan n'est pas exécuté : le moteur de test remplace celui du
      démarrage applicatif, aucun ``create_all`` implicite ;
    - chaque requête HTTP obtient sa propre session, comme en production.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    app: FastAPI
    factory: async_sessionmaker[AsyncSession]
    test_client: AsyncClient
    # ─────────────────────────────────

    # [STEP 1] Assembler l'application et la factory de test → app isolée de la dev
    app = create_app()
    factory = async_sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)

    # [STEP 2] Surcharger get_db → toute dépendance DB résout vers la base de test
    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        """Fournit une session de test par requête, image de ``get_db``."""
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    # [STEP 3] Céder le client ASGI → requêtes traitées sans serveur ni lifespan
    async with AsyncClient(
        base_url="http://testserver", transport=ASGITransport(app=app)
    ) as test_client:
        yield test_client


@pytest.fixture(scope="session")
async def db_engine() -> AsyncIterator[AsyncEngine]:
    """Moteur async lié à la base de test, schéma posé pour la session.

    Invariants :
    - ``drop_all`` avant ``create_all`` : le schéma reflète exactement les
      modèles courants, jamais un résidu de session précédente ;
    - les migrations Alembic sont validées séparément par le gate du jalon
      (``make db-migrate``), pas par la suite de tests (D10).
    """
    # ─── VARIABLE DECLARATION ZONE ───
    engine: AsyncEngine
    # ─────────────────────────────────

    # [STEP 1] Garantir l'existence de la base de test → CREATE DATABASE si besoin
    await _create_database_if_missing()

    # [STEP 2] Créer le moteur et reposer le schéma → tables alignées sur les modèles
    engine = create_async_engine(_replace_database_name(TEST_DATABASE_NAME, settings.database_url))
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    # [STEP 3] Céder le moteur puis le libérer → aucune connexion ne survit à la session
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Session async directe sur la base de test, pour les assertions hors API.

    Invariant : mêmes réglages que la factory applicative (``autoflush=False``,
    ``expire_on_commit=False``) — les tests observent le comportement exact
    des services.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    factory: async_sessionmaker[AsyncSession]
    session: AsyncSession
    # ─────────────────────────────────

    # [STEP 1] Construire la factory liée au moteur de test → réglages applicatifs répliqués
    factory = async_sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)

    # [STEP 2] Céder une session → fermeture garantie en sortie de contexte
    async with factory() as session:
        yield session
