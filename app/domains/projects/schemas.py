# [FILE] — app/domains/projects/schemas.py
# [SCHEMA]
# synthesis: The 4 Pydantic schemas of the projects domain carry the contract of the Project entity.
# domain: projects
# schemas: ProjectBase(BaseModel), ProjectCreate(ProjectBase), ProjectRead(ProjectBase),
#   ProjectUpdate(BaseModel)
# entity: Project
# [/SCHEMA]
"""Pydantic schemas of the projects domain.

Pure data, no logic and no methods: four classes (Base, Create, Read,
Update) in alphabetical order. ``organization_id`` only appears on
Create and Read — the organization is not modifiable in Phase 2;
``description`` carries the same empty-string default as the column;
maximum lengths are aligned with the ``models.py`` columns.
"""

# ─── IMPORTS ───
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ──────────────

# [CODE_START]


class ProjectBase(BaseModel):
    """Fields shared by project writes and reads."""

    description: str = ""
    name: str = Field(max_length=100)


class ProjectCreate(ProjectBase):
    """POST body — shared fields plus the organization, fixed at creation."""

    organization_id: int


class ProjectRead(ProjectBase):
    """API response — full state, organization and timestamps included."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    created_at: datetime
    updated_at: datetime


class ProjectUpdate(BaseModel):
    """PATCH body — name and description only, ``exclude_unset`` semantics."""

    description: str | None = None
    name: str | None = Field(default=None, max_length=100)
