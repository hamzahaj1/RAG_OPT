# Phase 1 — Plan technique détaillé

**Source** : `.specify/phase1_fondation.md`, CLAUDE.md sections 2–5.

---

## Architecture globale Phase 1

```
Jalon 1 (Infra)
    ↓ dépend de rien
Jalon 2 (Noyau FastAPI)
    ↓ dépend de Jalon 1 (docker-compose, .env.example)
Jalon 3 (Alembic)
    ↓ dépend de Jalon 2 (config.py, database.py)
```

Chaque jalon est autonome et validable.

---

## Jalon 1 — Infrastructure & Orchestration

### Fichiers à créer

1. **`pyproject.toml`**
2. **`docker-compose.yml`**
3. **`Makefile`**
4. **.env.example**

### Dépendances entre fichiers

```
pyproject.toml
    ↓ (dépend de)
Makefile, docker-compose.yml (versionning Python, images)

.env.example
    ↓ (source de vérité pour les variables)
docker-compose.yml (POSTGRES_PASSWORD, POSTGRES_DB, etc.)
```

### Détail du fichier `pyproject.toml`

**Structure minimale** :

```toml
[tool.poetry]
name = "alpha-scope-rag"
version = "0.1.0"
description = "RAG pipeline for code analysis"
authors = ["Hamza Hajj <hajjamhamza33@gmail.com>"]
python = "^3.11"

[tool.poetry.dependencies]
fastapi = "^0.104.0"
sqlalchemy = "^2.0.0"
asyncpg = "^0.29.0"
pydantic = "^2.0.0"
pydantic-settings = "^2.0.0"
python-dotenv = "^1.0.0"
uvicorn = "^0.24.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
mypy = "^1.6.0"
ruff = "^0.1.0"
alembic = "^1.13.0"

[tool.mypy]
python_version = "3.11"
strict = true
warn_unused_ignores = true

[tool.ruff]
line-length = 100
target-version = "py311"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
```

**Critères** :
- Python 3.11+, strict
- Dépendances min : FastAPI, SQLAlchemy 2.0, asyncpg, Pydantic V2, pydantic-settings
- Dev : pytest, pytest-asyncio, mypy `strict`, ruff
- Alembic en dev
- MyPy et Ruff configurés dans `[tool.*]`

### Détail du fichier `docker-compose.yml`

**Services** :
- `postgres` : PostgreSQL 16, volume `postgres_data`, exposé port 5432
- `adminer` : Adminer, exposé port 8080

**Pas de** : backend, frontend, services additionnels.

**Environnement** : toutes les variables viennent de `.env` ou `.env.example`

**Exemple** :

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-alpha_scope_dev}
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-password}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres}"]
      interval: 10s
      timeout: 5s
      retries: 5

  adminer:
    image: adminer:latest
    ports:
      - "8080:8080"
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  postgres_data:
```

### Détail du fichier `Makefile`

**Cibles minimales** :

```makefile
.PHONY: up down logs db-migrate db-seed help

help:
	@echo "Available targets:"
	@echo "  make up           - Start Docker Compose (postgres, adminer)"
	@echo "  make down         - Stop Docker Compose"
	@echo "  make logs         - Show Docker Compose logs"
	@echo "  make db-migrate   - Run Alembic migrations"
	@echo "  make db-seed      - Seed the database (not implemented yet)"

up:
	docker-compose up -d
	@echo "✓ PostgreSQL started on localhost:5432"
	@echo "✓ Adminer started on localhost:8080"

down:
	docker-compose down

logs:
	docker-compose logs -f

db-migrate:
	@echo "Running migrations..."
	alembic upgrade head

db-seed:
	@echo "Seeding database (placeholder for Phase 2)..."
	python -m app.scripts.seed

.DEFAULT_GOAL := help
```

### Détail du fichier `.env.example`

**Structure** :

```bash
# Database
POSTGRES_DB=alpha_scope_dev
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/alpha_scope_dev

# FastAPI
DEBUG=true
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000

# Alembic
SQLALCHEMY_ECHO=false
```

**Critère** : lisible, commenté, aucune valeur secrète réelle (templates uniquement).

### Validation Jalon 1

```bash
# Copier .env.example → .env (local dev)
cp .env.example .env

# Démarrer l'infra
make up

# Vérifier
docker-compose ps
# postgres   → Up (healthy)
# adminer    → Up

# Vérifier connectivité DB
psql -h localhost -U postgres -d alpha_scope_dev -c "SELECT 1;"
# Doit répondre (1)

# Vérifier Adminer
curl http://localhost:8080/
# Doit répondre 200

# Arrêter
make down
```

---

## Jalon 2 — Noyau FastAPI & Accès DB

### Fichiers à créer

1. **`app/core/config.py`** — Settings singleton
2. **`app/core/database.py`** — Moteur async, sessions, get_db()
3. **`app/main.py`** — FastAPI, lifespan, routeurs

### Dépendances entre fichiers

```
.env
    ↓
config.py (settings singleton)
    ↓
database.py (DSN depuis config.py)
    ↓
main.py (dépend de database.py pour get_db())
```

### Détail du fichier `app/core/config.py`

**Signature et zones** :

```python
# [FILE] — app/core/config.py
"""Configuration management via pydantic-settings."""

# ─── IMPORTS ───
import logging
from typing import Optional

from pydantic_settings import BaseSettings
# ─────────────────

# [CODE_START]

class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # Zone B — Déclaration des champs
    database_url: str
    postgres_db: str
    postgres_user: str
    postgres_password: str
    debug: bool = False
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    sqlalchemy_echo: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    # Zone C — Méthodes
    def get_database_url(self) -> str:
        """Return DSN for AsyncEngine."""
        return self.database_url

# Singleton global
settings = Settings()
```

**Critères** :
- Typage strict sur tous les champs
- Lue depuis `.env` (ou `.env.example`)
- DSN PostgreSQL construit ou fourni directement
- Gestion d'erreur silencieuse sur variables manquantes (valeurs par défaut)
- Export `settings` singleton

### Détail du fichier `app/core/database.py`

**Signature et zones** :

```python
# [FILE] — app/core/database.py
"""Database engine, sessions, and FastAPI dependency."""

# ─── IMPORTS ───
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings
# ─────────────────

# [CODE_START]

Base = declarative_base()

async def init_db_engine() -> AsyncEngine:
    """Create async SQLAlchemy engine."""
    engine: AsyncEngine = create_async_engine(
        settings.database_url,
        echo=settings.sqlalchemy_echo,
        pool_size=10,
        max_overflow=20,
    )
    return engine

async_session_factory = sessionmaker(
    bind=None,  # Will be set in main.py
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to inject database session."""
    async with async_session_factory() as session:
        yield session
```

**Critères** :
- Moteur async via `create_async_engine(...)`
- `Base` (declarative_base) pour modèles
- `AsyncSessionFactory` (sessionmaker)
- `get_db()` = seule porte d'accès aux sessions
- Typage strict sur tous les params
- Pas de logique métier

### Détail du fichier `app/main.py`

**Signature et zones** :

```python
# [FILE] — app/main.py
"""FastAPI application factory and lifecycle management."""

# ─── IMPORTS ───
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import settings
from app.core.database import Base, async_session_factory, init_db_engine
# ─────────────────

# [CODE_START]

logger = logging.getLogger(__name__)

# Global engine reference
_engine: AsyncEngine | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: startup and shutdown events."""
    # Startup
    global _engine
    logger.info("Starting up: initializing database engine...")
    _engine = await init_db_engine()
    async_session_factory.configure(bind=_engine)
    
    # Create tables (only for dev; use Alembic in production)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database engine ready.")
    
    yield
    
    # Shutdown
    logger.info("Shutting down: closing database engine...")
    if _engine:
        await _engine.dispose()
    logger.info("Shutdown complete.")

def create_app() -> FastAPI:
    """Create FastAPI application instance."""
    app = FastAPI(
        title="Alpha-Scope RAG",
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )
    
    # Placeholder: routers will be included here
    # from app.domains.users.router import router as users_router
    # app.include_router(users_router, prefix="/api/users")
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok"}
    
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
```

**Critères** :
- Lifespan (startup/shutdown) pour DB
- Crée tables au démarrage (dev-only; Alembic en prod)
- Point de montage des routeurs (commenté, structure prête)
- `/health` endpoint de santé
- Typé strictement

### Structure de répertoires attendue

```
app/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── config.py
│   └── database.py
├── domains/  # Vide pour l'instant, sera rempli en Phase 2
│   └── __init__.py
├── scripts/  # Vide pour l'instant
│   └── __init__.py
└── main.py
```

### Validation Jalon 2

```bash
# Installer dépendances
poetry install

# Vérifier types
mypy app/ --strict

# Vérifier style
ruff check app/

# Démarrer l'app
make up  # (PostgreSQL doit tourner)
python -m app.main

# Vérifier endpoints (dans un autre terminal)
curl http://localhost:8000/health
# {"status":"ok"}

curl http://localhost:8000/docs
# Swagger UI charge correctement

# Arrêter
make down
```

---

## Jalon 3 — Alembic Async

### Fichiers à créer/configurer

1. **`alembic/env.py`** — Async runtime
2. **`alembic.ini`** — Configuration (à la racine, convention standard)
3. **`alembic/versions/`** — Dossier pour migrations (vide au départ)
4. **`alembic/script.py.mako`** — Template de migration (généré par alembic init)

### Dépendances entre fichiers

```
config.py
    ↓
database.py
    ↓
env.py (imports Base, DSN depuis settings)
```

### Détail du fichier `alembic/env.py`

**Signature** :

```python
# [FILE] — alembic/env.py
"""Alembic environment configuration for async SQLAlchemy."""

# ─── IMPORTS ───
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from alembic import context
from app.core.config import settings
from app.core.database import Base
# ─────────────────

# [CODE_START]

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable: AsyncEngine = create_async_engine(
        settings.database_url,
        poolclass=pool.NullPool,
    )
    
    async with connectable.begin() as connection:
        await connection.run_sync(do_run_migrations)
    
    await connectable.dispose()

def do_run_migrations(connection: Connection) -> None:
    """Execute migrations within a sync context."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )
    with context.begin_transaction():
        context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

### Détail du fichier `alembic.ini` (racine)

**Sections critiques** :

```ini
[alembic]
sqlalchemy.url = driver://user:pass@localhost/dbname

# Use the commented-out sqlalchemy.url to override from env
# sqlalchemy.url =

version_path_separator = :
script_location = alembic

[loggers]
keys = root,sqlalchemy

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

**Critère** : `sqlalchemy.url` sera ignoré en faveur de `settings.database_url` dans `env.py`. Fichier situé à la racine du projet, pas dans `alembic/`.

### Validation Jalon 3

```bash
# Vérifier Alembic est configuré
alembic current
# Should show: <base>

# Créer une migration vide (test)
alembic revision -m "init_base"
# alembic/versions/xxxx_init_base.py

# Appliquer migrations
make db-migrate
# INFO [alembic.runtime.migration] Context impl AsyncPgDialect+asyncpg
# INFO [alembic.runtime.migration] Will assume TPC on commit...

# Vérifier état
alembic current
# <should show a migration hash>

# Vérifier base de données
psql -h localhost -U postgres -d alpha_scope_dev -c "\dt"
# (tables créées par SQLAlchemy Base.metadata.create_all())
```

---

## Ordre d'exécution strict

1. **Jalon 1** : Créer infra (pyproject.toml, docker-compose.yml, Makefile, .env.example)
   - Valider : `make up` démarre PostgreSQL
   - Valider : Adminer accessible
2. **Jalon 2** : Créer noyau (config.py, database.py, main.py)
   - Valider : MyPy strict passe
   - Valider : Ruff passe
   - Valider : `/health` répond
   - Valider : `/docs` charge
3. **Jalon 3** : Créer Alembic
   - Valider : `make db-migrate` passe
   - Valider : Schéma initialisé dans PostgreSQL

---

## Critères de qualité transversaux

Pour tous les fichiers Python :

- **Typage strict** : 100 % annoté, MyPy `strict` passe
- **Formatage** : Ruff passe
- **Structure** : `[FILE]`, `[CODE_START]`, zones B/C
- **Pas encore d'en-têtes [RAG]** : seront générés en phase 3
- **Pas de clever** : prévisibilité structurelle > concision
- **Test permanent** : est-ce qu'un senior FastAPI embaucherait quelqu'un qui a écrit ça ? → OUI

---

## Dépendances externales

- Python 3.11+
- Poetry (installé)
- Docker & Docker Compose
- PostgreSQL 16 (via image Docker)

Aucune autre dépendance système requise.
