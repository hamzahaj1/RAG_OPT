# [FILE] — tests/unit/corpus_fixtures.py
"""Mini-corpus de fixture pour les tests de l'outillage phase 3.

Reproduit en miniature la géométrie du corpus réel — noyau ``core``,
domaine ``users`` complet, domaines ``organizations``/``projects``
réduits, ``scripts/seed.py`` avec import aliasé — afin de tester la
résolution du graphe (T057) et l'insertion des en-têtes (T059) sur des
attendus exacts et indépendants du corpus de production. Le contenu des
fichiers est une donnée de test : il n'est pas soumis au Standard V3.
"""

# ─── IMPORTS ───
from pathlib import Path

# ──────────────

# [CODE_START]

FIXTURE_CONFIG: str = '''"""Config de fixture."""


class Settings:
    """Paramètres factices."""


settings = Settings()
'''

FIXTURE_DATABASE: str = '''"""Noyau DB de fixture."""


def get_db():
    """Session factice."""
    yield None


def helper_shared():
    """Aide transverse appelée par trois domaines."""
    return None
'''

FIXTURE_MAIN: str = '''"""Assemblage de fixture."""

from app.core.config import settings


def create_app():
    """Application factice lisant la configuration."""
    return settings
'''

FIXTURE_ORG_SERVICES: str = '''"""Services organizations de fixture."""

from app.core.database import helper_shared


def poke():
    """Référence le noyau partagé."""
    return helper_shared()
'''

FIXTURE_PROJECT_SERVICES: str = '''"""Services projects de fixture."""

from app.core.database import helper_shared


def poke():
    """Référence le noyau partagé."""
    return helper_shared()
'''

FIXTURE_SEED: str = '''"""Seed de fixture — import aliasé de module."""

import app.domains.users.services as users_services


async def run(db):
    """Crée via le service, à travers l'alias de module."""
    return await users_services.create_user(db, None)
'''

FIXTURE_COMMENT_MODELS: str = '''# [FILE] — app/domains/comments/models.py
"""Modèle comments de fixture — double FK, politiques opposées."""

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column


class Comment:
    """Modèle factice : auteur bloquant, tâche contenante."""

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
'''

FIXTURE_TASK_MODELS: str = '''# [FILE] — app/domains/tasks/models.py
"""Modèle tasks de fixture — assignation détachable."""

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column


class Task:
    """Modèle factice : l'assigné se détache en SET NULL."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
'''

FIXTURE_USER_MODELS: str = '''# [FILE] — app/domains/users/models.py
"""Modèle users de fixture."""

from sqlalchemy.orm import Mapped, mapped_column


class User:
    """Modèle factice portant sa table."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
'''

FIXTURE_USER_ROUTER: str = '''"""Routeur users de fixture."""

from fastapi import APIRouter, Depends

from app.core.database import get_db
from app.domains.users import services

router = APIRouter()


@router.post("")
async def create_user(data, db=Depends(get_db)):
    """Endpoint délégant au service."""
    return await services.create_user(db, data)
'''

FIXTURE_USER_SCHEMAS: str = '''# [FILE] — app/domains/users/schemas.py
"""Schémas users de fixture."""

from pydantic import BaseModel


class UserCreate(BaseModel):
    """Schéma factice."""
'''

FIXTURE_USER_SERVICES: str = '''"""Services users de fixture."""

from sqlalchemy import select

from app.core.database import helper_shared
from app.domains.users.models import User


async def create_user(db, data):
    """Crée un utilisateur factice."""
    existing: User | None
    user: User
    existing = await db.scalar(select(User))
    if existing is not None:
        return existing
    helper_shared()
    user = User()
    db.add(user)
    return user
'''


def build_fixture_corpus(root: Path) -> Path:
    """Matérialise le mini-corpus sous ``root/app`` et retourne ce dossier.

    Invariant : la structure imite le corpus réel (mêmes conventions de
    chemins ``app/core``, ``app/domains/<d>``, ``app/scripts``) pour que
    la qualification des modules soit identique à la production.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    app_dir: Path
    contents: dict[str, str]
    relative: str
    target: Path
    # ─────────────────────────────────────────

    # [STEP 1] Décrire l'arborescence complète → un contenu par chemin relatif
    app_dir = root / "app"
    contents = {
        "__init__.py": "",
        "core/__init__.py": "",
        "core/config.py": FIXTURE_CONFIG,
        "core/database.py": FIXTURE_DATABASE,
        "domains/__init__.py": "",
        "domains/comments/__init__.py": "",
        "domains/comments/models.py": FIXTURE_COMMENT_MODELS,
        "domains/organizations/__init__.py": "",
        "domains/organizations/services.py": FIXTURE_ORG_SERVICES,
        "domains/projects/__init__.py": "",
        "domains/projects/services.py": FIXTURE_PROJECT_SERVICES,
        "domains/tasks/__init__.py": "",
        "domains/tasks/models.py": FIXTURE_TASK_MODELS,
        "domains/users/__init__.py": "",
        "domains/users/models.py": FIXTURE_USER_MODELS,
        "domains/users/router.py": FIXTURE_USER_ROUTER,
        "domains/users/schemas.py": FIXTURE_USER_SCHEMAS,
        "domains/users/services.py": FIXTURE_USER_SERVICES,
        "main.py": FIXTURE_MAIN,
        "scripts/__init__.py": "",
        "scripts/seed.py": FIXTURE_SEED,
    }

    # [STEP 2] Écrire chaque fichier → mini-corpus prêt pour l'analyse
    for relative, content in contents.items():
        target = app_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return app_dir
