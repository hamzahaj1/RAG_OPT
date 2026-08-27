# Phase 1 — Fondation (Spec Kit)

**Source de vérité** : CLAUDE.md, section 8, jalons 0–3.

## Périmètre exact

Trois jalons séquentiels, rien d'autre. Chacun doit être validé avant le suivant.

---

## Jalon 1 : Infrastructure & Orchestration

### Livrable

- `pyproject.toml` — Poetry, dépendances phase 1 (FastAPI, SQLAlchemy, asyncpg, Pydantic, etc.)
- `docker-compose.yml` — PostgreSQL 16, Adminer (port 8080)
- `Makefile` — cibles `up`, `down`, `logs`, `db-migrate`, `db-seed`
- `.env.example` — template, DSN PostgreSQL, DEBUG, etc.

### Critère de validation

```bash
make up
# PostgreSQL démarre et répond sur localhost:5432
# Adminer accessible sur localhost:8080
# Aucune erreur dans les logs
```

### Règles

- `docker-compose.yml` : volumes pour PostgreSQL, pas de montage de code live
- `pyproject.toml` : Python 3.11+, dépendances min et dev séparées, format standard Poetry
- `.env.example` : lisible, commenté, aucune valeur réelle (templates only)
- `Makefile` : cibles idempotentes, échos explicites

---

## Jalon 2 : Noyau FastAPI & Accès DB

### Livrable

- `app/core/config.py` — Pydantic Settings, DSN PostgreSQL, variables d'environnement
- `app/core/database.py` — Moteur SQLAlchemy async, AsyncSessionFactory, fonction `get_db()` pour DI
- `app/main.py` — Montage FastAPI, includer les routeurs, cycle de vie DB (startup/shutdown), structure prête pour les domaines

### Critère de validation

```bash
make up
# Backend démarre
python -m app.main  # ou via uvicorn
# http://localhost:8000/docs répond (Swagger UI)
# /health ou équivalent répond 200
# Pas d'erreurs de typage MyPy ou Ruff
```

### Règles pour `app/core/config.py`

- Classe `Settings` avec `pydantic_settings.BaseSettings`
- Variables : `DATABASE_URL`, `DEBUG`, `LOG_LEVEL`, ports, etc.
- Typage strict sur tous les champs
- Gestion d'erreur sur DSN malformé

### Règles pour `app/core/database.py`

- Moteur asynchrone : `create_async_engine(...)`
- `AsyncSessionFactory = sessionmaker(..., async_engine)`
- Fonction `async def get_db()` pour dépendance FastAPI
- Exporte `Base` (declarative_base) pour modèles SQLAlchemy
- Pas de logique métier

### Règles pour `app/main.py`

- Instance FastAPI unique
- Import des routeurs (vides pour now, structure prête)
- Cycle de vie : startup crée tables, shutdown ferme sessions
- Structure lisible, pas d'imbrication

### Structure Python attendue

Chaque fichier `.py` en `app/core/` :

```python
# [FILE] — app/core/<nom>.py
"""Module description."""

# ─── IMPORTS ───
import logging
from typing import ...
from fastapi import ...
# ─────────────────

# [CODE_START]

# Fonctions/classes, zones B/C pour chaque fonction
async def function_name(...):
    # Zone B — variables déclarées, triées
    var1: Type
    var2: Type = default
    
    # Zone C — algorithme, [STEP] si complexe
    ...
```

**Marqueurs obligatoires** : `[FILE]`, `[CODE_START]`. Zones B/C respectées.
**Pas encore** : en-têtes `[RAG]` (générés en phase 3).

---

## Jalon 3 : Migrations Alembic (Async)

### Livrable

- `alembic/env.py` — Configuré pour async, `sqlalchemy.asyncio`
- `alembic/alembic.ini` — DSN depuis `config.py`, version_path_separator

### Critère de validation

```bash
make db-migrate
# Alembic crée les tables de base (métadonnées SQLAlchemy)
# `alembic heads` répond
# Pas d'erreur
```

### Règles

- `alembic/env.py` : utilise `AsyncEngine`, `run_async()`
- DSN lue depuis `settings` (importée de `app.core.config`)
- Migrations vides pour now (les domaines ajouteront leurs schémas)
- Format strict, zéro boilerplate custom

---

## Hors périmètre

- ❌ Aucun domaine métier (`users`, `organizations`, etc.)
- ❌ Aucun frontend
- ❌ Aucun script de métadonnées
- ❌ Aucun test (tests en phase 2+)
- ❌ Aucune authentification

---

## Ordre de construction

1. Jalon 1 (infra) → valider `make up`
2. Jalon 2 (noyau) → valider `/docs` et démarrage
3. Jalon 3 (migrations) → valider `make db-migrate`

---

## Rappels Alpha-Scope

- **Test permanent** : est-ce qu'un senior FastAPI embaucherait quelqu'un qui a écrit ça ?
  → OUI pour cette fondation, ou c'est rejeté.
- **Typage strict** : 100 % annoté, MyPy `strict` mode
- **Norme de régularité** : structure prévisible, parsable, pas de clever
- **CLAUDE.md gagne** : en cas de doute, relire section 2 (contrainte non négociable)
