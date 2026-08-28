# [FILE] — app/domains/comments/models.py
# [MODEL]
# synthese: Un Comment n'est référencé par aucune table.
# entity: Comment
# table: comments
# columns: author_id, content, created_at, id, task_id, updated_at
# fks: author_id -> users.id [RESTRICT], task_id -> tasks.id [CASCADE]
# referenced_by: none
# [/MODEL]
"""Modèle SQLAlchemy du domaine comments.

Dernier maillon du graphe relationnel, relation la plus imbriquée :
``task_id`` référence ``tasks.id`` en ``ondelete=CASCADE`` (la suppression
d'une tâche emporte ses commentaires — fin de l'axe de contenance
projects → tasks → comments, DB seule) ; ``author_id`` référence
``users.id`` en ``ondelete=RESTRICT`` (un auteur de commentaires ne peut
pas être supprimé — backstop DB du 409 applicatif, D2). Aucune navigation
ORM inter-domaines (pas de ``relationship()`` en Phase 2).
"""

# ─── IMPORTS ───
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# ──────────────

# [CODE_START]


class Comment(Base):
    """Commentaire rattaché à une tâche, écrit par un utilisateur.

    Invariants :
    - ``task_id`` pointe toujours vers une tâche existante : vérifié par
      le service (404 à l'écriture) et par la FK ``CASCADE`` — la
      suppression de la tâche emporte le commentaire (jamais l'inverse) ;
    - ``author_id`` pointe toujours vers un utilisateur existant : vérifié
      par le service (404 à l'écriture) ; la suppression de l'auteur est
      refusée tant que le commentaire existe (409 applicatif, FK
      ``RESTRICT`` en backstop — D2) ;
    - ni la tâche ni l'auteur ne sont modifiables après création
      (Phase 2) ; ``content`` n'est jamais NULL.
    """

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    content: Mapped[str] = mapped_column(Text)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )
