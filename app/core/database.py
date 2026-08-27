# [FILE] — app/core/database.py
"""Moteur SQLAlchemy async, factory de sessions et dépendance FastAPI.

``get_db`` est la seule porte d'accès aux sessions DB du projet : aucun
module ne crée de session directement depuis la factory. Le moteur est
créé au démarrage de l'application (lifespan) puis lié à la factory via
``async_session_factory.configure(bind=engine)``.
"""

# ─── IMPORTS ───
from collections.abc import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ──────────────

# [CODE_START]

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base déclarative commune à tous les modèles SQLAlchemy du projet.

    Invariant : toute contrainte (PK, FK, UNIQUE, CHECK, index) reçoit un
    nom déterministe via ``NAMING_CONVENTION`` — condition des migrations
    autogénérées reproductibles (D3), jamais de nom choisi par PostgreSQL.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Fournit une session DB par requête HTTP (dépendance FastAPI).

    Invariants :
    - une requête HTTP = une session, fermée quoi qu'il arrive en sortie ;
    - la factory doit avoir été liée à un moteur au démarrage (lifespan),
      sinon l'ouverture de session échoue.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    session: AsyncSession
    # ─────────────────────────────────────────

    # [STEP 1] Ouvrir une session depuis la factory → session liée au moteur courant
    async with async_session_factory() as session:
        # [STEP 2] Céder la session à l'appelant → fermeture garantie en sortie de contexte
        yield session


def init_db_engine() -> AsyncEngine:
    """Crée le moteur async du projet à partir du DSN de ``settings``.

    Cas limites :
    - aucun ping n'est émis ici : un DSN invalide n'échoue qu'à la
      première connexion réelle (synchronisation du schéma au démarrage).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    engine: AsyncEngine
    # ─────────────────────────────────────────

    # [STEP 1] Construire le moteur depuis le DSN → engine prêt, aucune connexion ouverte
    engine = create_async_engine(
        settings.database_url,
        echo=settings.sqlalchemy_echo,
        max_overflow=20,
        pool_size=10,
    )
    return engine
