# Phase 1 — Tâches atomiques

**Source** : `.specify/phase1_plan_technique.md`

Chaque tâche est la plus granulaire possible. Les jalons sont terminés par une tâche de validation explicite.

---

## Jalon 1 — Infrastructure & Orchestration

### Tâche 1.1 — Créer `pyproject.toml`

**Livrables** :
- Fichier `pyproject.toml` à la racine
- Python 3.11+, Poetry
- Dépendances de production : fastapi, sqlalchemy, asyncpg, pydantic, pydantic-settings, python-dotenv, uvicorn
- Dépendances de dev : pytest, pytest-asyncio, mypy, ruff, alembic
- Sections `[tool.mypy]` (strict = true) et `[tool.ruff]` (line-length = 100)

**Critères d'acceptation** :
```bash
poetry lock  # Fonctionne sans erreur
poetry install --no-root  # Installe toutes les dépendances
```

---

### Tâche 1.2 — Créer `docker-compose.yml`

**Livrables** :
- Fichier `docker-compose.yml` à la racine
- Service `postgres` : PostgreSQL 16, variables POSTGRES_DB/POSTGRES_USER/POSTGRES_PASSWORD, port 5432, volume `postgres_data`, healthcheck
- Service `adminer` : Adminer, port 8080, dépendance sur postgres (service_healthy)
- Aucun autre service (backend, frontend viendront plus tard)

**Critères d'acceptation** :
```bash
docker-compose config  # Pas d'erreur YAML
```

---

### Tâche 1.3 — Créer `Makefile`

**Livrables** :
- Fichier `Makefile` à la racine
- Cibles : `help`, `up`, `down`, `logs`, `db-migrate`, `db-seed`
- Echos explicites, idempotence

**Critères d'acceptation** :
```bash
make help  # Affiche l'aide
make up    # Lance sans erreur
```

---

### Tâche 1.4 — Créer `.env.example`

**Livrables** :
- Fichier `.env.example` à la racine
- Variables : POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, DATABASE_URL, DEBUG, LOG_LEVEL, API_HOST, API_PORT, SQLALCHEMY_ECHO
- Commentaires explicatifs
- Aucune valeur secrète réelle

**Critères d'acceptation** :
```bash
cat .env.example  # Lisible, commenté
```

---

### Tâche 1.5 — Validation Jalon 1 : Infrastructure opérationnelle

**Prérequis** : Tâches 1.1–1.4 terminées.

**Procédure** :

```bash
# Copier .env.example en .env pour le dev local
cp .env.example .env

# Démarrer l'infra
make up

# Vérifier que les services démarrent
docker-compose ps
# postgres   UP (healthy)
# adminer    UP

# Attendre ~3s pour PostgreSQL soit prêt
sleep 3

# Vérifier connectivité PostgreSQL
psql -h localhost -U postgres -d alpha_scope_dev -c "SELECT 1;"
# Doit retourner (1)

# Vérifier Adminer est accessible
curl -s http://localhost:8080/ | grep -q "Adminer"
# Doit retourner 0

# Arrêter les services
make down
```

**Critère de passage** : Tous les tests ci-dessus passent. ✅ Jalon 1 VALIDÉ.

---

## Jalon 2 — Noyau FastAPI & Accès DB

### Tâche 2.1 — Créer répertoires `app/`

**Livrables** :
- `app/__init__.py` (vide)
- `app/core/__init__.py` (vide)
- `app/domains/__init__.py` (vide)
- `app/scripts/__init__.py` (vide)

**Critères d'acceptation** :
```bash
ls -la app/core/  # Fichiers __init__.py présents
```

---

### Tâche 2.2 — Créer `app/core/config.py`

**Livrables** :
- Classe `Settings` héritée de `BaseSettings`
- Champs : database_url, postgres_db, postgres_user, postgres_password, debug, log_level, api_host, api_port, sqlalchemy_echo
- Typage strict (`Optional`, `bool`, `str`, `int`)
- Config `env_file = ".env"`
- Export singleton `settings = Settings()`

**Critères d'acceptation** :
```bash
python -c "from app.core.config import settings; print(settings.database_url)"
# Doit afficher le DSN PostgreSQL
```

---

### Tâche 2.3 — Créer `app/core/database.py`

**Livrables** :
- Import et utilisation de `app.core.config.settings`
- `Base = declarative_base()`
- Fonction `async def init_db_engine()` → AsyncEngine
- `async_session_factory = sessionmaker(...)` (sans bind initial)
- Fonction `async def get_db()` → AsyncGenerator[AsyncSession, None]

**Critères d'acceptation** :
```bash
python -c "from app.core.database import Base, get_db; print(Base, get_db)"
# Doit afficher les objets sans erreur
```

---

### Tâche 2.4 — Créer `app/main.py`

**Livrables** :
- Import de config, database, lifespan
- Fonction `lifespan(app: FastAPI)` : asynccontextmanager avec startup/shutdown
  - Startup : init engine, configure async_session_factory, create_all(Base.metadata)
  - Shutdown : dispose engine
- Fonction `create_app()` → FastAPI
- Instance `app = create_app()`
- Endpoint `/health` → `{"status": "ok"}`
- Bloc `if __name__ == "__main__"` pour uvicorn

**Critères d'acceptation** :
```bash
python -m app.main &
sleep 2
curl http://localhost:8000/health
# {"status":"ok"}
kill %1
```

---

### Tâche 2.5 — Appliquer Ruff sur `app/`

**Livrables** :
- Formatter et linter tout le code Python de `app/` avec Ruff

**Critères d'acceptation** :
```bash
ruff check app/ --fix
# Aucune erreur restante
```

---

### Tâche 2.6 — Appliquer MyPy strict sur `app/`

**Livrables** :
- Vérifier le typage strict avec MyPy

**Critères d'acceptation** :
```bash
mypy app/ --strict
# Success: no issues found in 5 source files
```

---

### Tâche 2.7 — Validation Jalon 2 : Noyau FastAPI opérationnel

**Prérequis** : Tâches 2.1–2.6 terminées, Jalon 1 validé.

**Procédure** :

```bash
# Vérifier que PostgreSQL est lancé (depuis Jalon 1)
make up

# Installer les dépendances (si not already done)
poetry install

# Vérifier MyPy strict
mypy app/ --strict
# Success

# Vérifier Ruff
ruff check app/
# No issues

# Démarrer l'app
python -m app.main &
sleep 2
APP_PID=$!

# Test 1: /health répond
curl http://localhost:8000/health
# {"status":"ok"}

# Test 2: /docs charge (Swagger UI)
curl -s http://localhost:8000/docs | grep -q "swagger-ui"
# Retourne 0

# Test 3: Schéma OpenAPI disponible
curl -s http://localhost:8000/openapi.json | grep -q '"openapi"'
# Retourne 0

# Arrêter l'app
kill $APP_PID

# Arrêter PostgreSQL
make down
```

**Critère de passage** : Tous les tests passent. ✅ Jalon 2 VALIDÉ.

---

## Jalon 3 — Alembic Async

### Tâche 3.1 — Créer structure Alembic

**Livrables** :
- Répertoires : `alembic/versions/`, `alembic/`
- Fichiers vides/template : `alembic/script.py.mako`, `alembic/versions/.gitkeep`

**Critères d'acceptation** :
```bash
ls -la alembic/
# versions/, script.py.mako présents
```

---

### Tâche 3.2 — Créer `alembic/env.py`

**Livrables** :
- Imports de `asyncio`, `sqlalchemy.ext.asyncio`, `app.core.config`, `app.core.database`
- Fonctions `run_migrations_offline()`, `run_migrations_online()`, `do_run_migrations()`
- Utilise `settings.database_url` et `Base.metadata`
- Conditionnel `if context.is_offline_mode()`

**Critères d'acceptation** :
```bash
python -c "from alembic.env import config, target_metadata; print(target_metadata)"
# Doit afficher l'objet MetaData
```

---

### Tâche 3.3 — Créer `alembic.ini` (racine)

**Livrables** :
- Fichier `alembic.ini` à la racine du projet (convention Alembic standard)
- Sections : `[alembic]`, `[loggers]`, `[handlers]`, `[formatters]`
- `sqlalchemy.url` laissé vide (sera fourni par env.py)
- `version_path_separator = :`
- `script_location = alembic`

**Critères d'acceptation** :
```bash
cat alembic.ini | grep "script_location"
# script_location = alembic
```

---

### Tâche 3.4 — Validation Jalon 3 : Alembic operationnel

**Prérequis** : Tâches 3.1–3.3 terminées, Jalon 1 + Jalon 2 validés.

**Procédure** :

```bash
# Vérifier que PostgreSQL est lancé
make up

# Vérifier l'état d'Alembic avant migration
alembic current
# <base> (ou similaire)

# Appliquer les migrations (none yet, mais la commande doit fonctionner)
make db-migrate
# INFO [alembic.runtime.migration] Context impl AsyncPgDialect+asyncpg

# Vérifier l'état après migration
alembic current
# Doit afficher un hash (ou <base>)

# Vérifier que la base de données est prête
psql -h localhost -U postgres -d alpha_scope_dev -c "\dt"
# Doit retourner 0 rows (aucune table créée encore, c'est normal — les domaines les ajouteront)

# Arrêter
make down
```

**Critère de passage** : `make db-migrate` passe sans erreur. ✅ Jalon 3 VALIDÉ.

---

## Résumé des tâches par jalon

| Jalon | Tâches | Validation |
|---|---|---|
| 1 | 1.1–1.4 | 1.5 (`make up` + services healthy) |
| 2 | 2.1–2.6 | 2.7 (MyPy + Ruff + `/health` + `/docs`) |
| 3 | 3.1–3.3 | 3.4 (`make db-migrate` passe) |

---

## Règles transversales

- **Ordre strict** : Jalon 1 → Jalon 2 → Jalon 3. Chaque jalon se termine par sa validation.
- **Atomicité** : Chaque tâche produit un livrables vérifiable, sans déborder sur les autres.
- **Zéro Phase 2** : Aucun domaine métier, aucun modèle SQLAlchemy autre que Base, aucun test Pytest.
- **Alpha-Scope** : Structure Python (`[FILE]`, `[CODE_START]`, zones B/C) respectée. Pas encore d'en-têtes [RAG] (phase 3).
- **Typage strict** : MyPy `strict` passe sur tout.
- **Formatage** : Ruff passe sur tout.

---

## Points de contrôle critiques

1. **Jalon 1** : PostgreSQL doit démarrer et répond au healthcheck
2. **Jalon 2** : App démarre, `/health` répond, `/docs` charge, MyPy strict passe
3. **Jalon 3** : `make db-migrate` fonctionne sans erreur
