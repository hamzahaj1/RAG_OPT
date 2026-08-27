# [FILE] — alembic/env.py
"""Environnement d'exécution Alembic pour migrations asynchrones.

Le DSN provient exclusivement du singleton ``settings`` — la valeur
``sqlalchemy.url`` d'``alembic.ini`` est ignorée. ``target_metadata``
pointe sur ``Base.metadata`` : pour que ``--autogenerate`` détecte un
modèle, son module doit être importé ici (point d'ancrage Phase 2).
"""

# ─── IMPORTS ───
import asyncio
from logging.config import fileConfig

from sqlalchemy import MetaData, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from alembic import context
from app.core.config import settings
from app.core.database import Base

# Point d'ancrage Phase 2 : importer ici les modèles de chaque domaine
# pour qu'ils s'enregistrent dans Base.metadata (détection autogenerate).
from app.domains.comments import models as comments_models  # noqa: F401
from app.domains.organizations import models as organizations_models  # noqa: F401
from app.domains.projects import models as projects_models  # noqa: F401
from app.domains.tasks import models as tasks_models  # noqa: F401
from app.domains.users import models as users_models  # noqa: F401

# ──────────────

# [CODE_START]

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata: MetaData = Base.metadata


def do_run_migrations(connection: Connection) -> None:
    """Exécute les migrations sur une connexion déjà ouverte.

    Invariant : appelée uniquement via ``run_sync`` — le contexte Alembic
    ne manipule jamais directement la connexion async.
    """
    # [STEP 1] Configurer le contexte sur la connexion → métadonnées cibles liées
    context.configure(connection=connection, target_metadata=target_metadata)

    # [STEP 2] Exécuter les migrations en transaction → schéma migré ou rollback complet
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    """Génère le SQL des migrations sans connexion à la base (mode offline).

    Cas limite : ``literal_binds`` inline les paramètres — réservé à la
    production de scripts SQL, jamais à une exécution réelle.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    url: str
    # ─────────────────────────────────────────

    # [STEP 1] Résoudre le DSN depuis settings → url unique, jamais alembic.ini
    url = settings.database_url

    # [STEP 2] Configurer le contexte sans connexion → rendu SQL littéral prêt
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    # [STEP 3] Exécuter les migrations en transaction → SQL émis sur la sortie
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Applique les migrations sur la base via un moteur async (mode online).

    Invariants :
    - ``NullPool`` : aucune connexion ne survit à la migration ;
    - le moteur est libéré même si la migration échoue en amont du commit.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    engine: AsyncEngine
    # ─────────────────────────────────────────

    # [STEP 1] Créer un moteur éphémère depuis settings → DSN asyncpg résolu
    engine = create_async_engine(settings.database_url, poolclass=pool.NullPool)

    # [STEP 2] Ouvrir une connexion et déléguer au contexte sync → migrations appliquées
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)

    # [STEP 3] Libérer le moteur → aucune connexion résiduelle
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
