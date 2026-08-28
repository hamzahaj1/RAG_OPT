# [FILE] — app/domains/organizations/schemas.py
# [SCHEMA]
# synthesis: The 4 Pydantic schemas of the organizations domain carry the contract of the
#   Organization entity.
# domain: organizations
# schemas: OrganizationBase(BaseModel), OrganizationCreate(OrganizationBase),
#   OrganizationRead(OrganizationBase), OrganizationUpdate(BaseModel)
# entity: Organization
# [/SCHEMA]
"""Pydantic schemas of the organizations domain.

Pure data, no logic and no methods: four classes (Base, Create, Read,
Update) in alphabetical order. ``owner_id`` only appears on Create and
Read — the owner is not modifiable in Phase 2; maximum lengths are
aligned with the ``models.py`` columns.
"""

# ─── IMPORTS ───
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ──────────────

# [CODE_START]


class OrganizationBase(BaseModel):
    """Fields shared by organization writes and reads."""

    name: str = Field(max_length=100)


class OrganizationCreate(OrganizationBase):
    """POST body — shared fields plus the owner, fixed at creation."""

    owner_id: int


class OrganizationRead(OrganizationBase):
    """API response — full state, owner and timestamps included."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime


class OrganizationUpdate(BaseModel):
    """PATCH body — only ``name`` is modifiable, ``exclude_unset`` semantics."""

    name: str | None = Field(default=None, max_length=100)
