# [FILE] — tests/integration/conftest.py
"""Nettoyage de la base de test entre chaque test d'intégration.

Fixture autouse volontairement limitée à ``tests/integration`` : les
tests unitaires (schémas, enums, helpers purs) restent exécutables sans
PostgreSQL (D10).
"""

# ─── IMPORTS ───
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.database import Base

# ──────────────

# [CODE_START]


@pytest.fixture(autouse=True)
async def _truncate_all_tables(db_engine: AsyncEngine) -> AsyncIterator[None]:
    """Remet la base de test à zéro après chaque test.

    Invariants :
    - ``TRUNCATE ... RESTART IDENTITY CASCADE`` : tables vides et séquences
      remises à 1 — chaque test démarre d'un état strictement identique ;
    - plus prévisible qu'un rollback : les services committent réellement
      pendant le test, le nettoyage se fait donc après coup (D10).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    table_names: str
    # ─────────────────────────────────────────

    # [STEP 1] Laisser le test s'exécuter → assertions faites sur un état committé
    yield

    # [STEP 2] Tronquer toutes les tables connues → base vide, identités remises à 1
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    async with db_engine.begin() as connection:
        await connection.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))
