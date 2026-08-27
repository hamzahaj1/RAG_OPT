# Data Model — Phase 2 : Domaines métier

**Feature**: `001-phase2-domains` | **Date**: 2026-08-27
**Références** : [spec.md](spec.md) (Key Entities), [research.md](research.md) (D1–D4, D12, D14)

Conventions transversales (appliquées aux cinq tables) :

- PK : `id` — `int` autoincrémenté (`Mapped[int]`, `primary_key=True`).
- Horodatages : `created_at`, `updated_at` — `DateTime(timezone=True)`,
  `server_default=func.now()` ; `updated_at` porte `onupdate=func.now()`.
- Contraintes nommées par la `naming_convention` de `Base.metadata` (D3).
- Ensembles fermés : enum Python `(str, Enum)` + colonne `String` +
  `CheckConstraint` nommée (D1). Jamais d'ENUM natif PostgreSQL.
- Toute colonne FK est indexée (`index=True`).

## Enums

| Enum | Module | Valeurs | Défaut |
|---|---|---|---|
| `UserRole` | `app/domains/users/models.py` | `admin`, `member` | `member` |
| `TaskStatus` | `app/domains/tasks/models.py` | `todo`, `in_progress`, `done` | `todo` |
| `TaskPriority` | `app/domains/tasks/models.py` | `low`, `medium`, `high` | `medium` |

## Table `users` — `app/domains/users/models.py`

| Colonne | Type SQL | Contraintes |
|---|---|---|
| `id` | `INTEGER` | PK |
| `email` | `VARCHAR(255)` | NOT NULL, UNIQUE, index |
| `full_name` | `VARCHAR(100)` | NOT NULL |
| `hashed_password` | `VARCHAR(255)` | NOT NULL — jamais exposé par l'API |
| `role` | `VARCHAR(20)` | NOT NULL, défaut `member`, CHECK `role IN ('admin','member')` (nom : `ck_users_role`) |
| `created_at` / `updated_at` | `TIMESTAMPTZ` | NOT NULL, cf. conventions |

## Table `organizations` — `app/domains/organizations/models.py`

| Colonne | Type SQL | Contraintes |
|---|---|---|
| `id` | `INTEGER` | PK |
| `name` | `VARCHAR(100)` | NOT NULL, UNIQUE |
| `owner_id` | `INTEGER` | NOT NULL, FK → `users.id` `ondelete=RESTRICT`, index |
| `created_at` / `updated_at` | `TIMESTAMPTZ` | NOT NULL |

## Table `projects` — `app/domains/projects/models.py`

| Colonne | Type SQL | Contraintes |
|---|---|---|
| `id` | `INTEGER` | PK |
| `name` | `VARCHAR(100)` | NOT NULL |
| `description` | `TEXT` | NOT NULL, défaut `''` (jamais NULL) |
| `organization_id` | `INTEGER` | NOT NULL, FK → `organizations.id` `ondelete=RESTRICT`, index |
| `created_at` / `updated_at` | `TIMESTAMPTZ` | NOT NULL |

Contrainte de table : UNIQUE `(organization_id, name)`.

## Table `tasks` — `app/domains/tasks/models.py`

| Colonne | Type SQL | Contraintes |
|---|---|---|
| `id` | `INTEGER` | PK |
| `title` | `VARCHAR(200)` | NOT NULL |
| `description` | `TEXT` | NOT NULL, défaut `''` |
| `status` | `VARCHAR(20)` | NOT NULL, défaut `todo`, CHECK `status IN ('todo','in_progress','done')` (`ck_tasks_status`) |
| `priority` | `VARCHAR(20)` | NOT NULL, défaut `medium`, CHECK `priority IN ('low','medium','high')` (`ck_tasks_priority`) |
| `project_id` | `INTEGER` | NOT NULL, FK → `projects.id` `ondelete=CASCADE`, index |
| `assignee_id` | `INTEGER` | **NULLABLE**, FK → `users.id` `ondelete=SET NULL`, index |
| `created_at` / `updated_at` | `TIMESTAMPTZ` | NOT NULL |

## Table `comments` — `app/domains/comments/models.py`

| Colonne | Type SQL | Contraintes |
|---|---|---|
| `id` | `INTEGER` | PK |
| `content` | `TEXT` | NOT NULL |
| `task_id` | `INTEGER` | NOT NULL, FK → `tasks.id` `ondelete=CASCADE`, index |
| `author_id` | `INTEGER` | NOT NULL, FK → `users.id` `ondelete=RESTRICT`, index |
| `created_at` / `updated_at` | `TIMESTAMPTZ` | NOT NULL |

## Sémantique de suppression (double couche, D2)

```
DELETE user         → 409 si propriétaire d'organisations (service + RESTRICT)
                    → 409 si auteur de commentaires      (service + RESTRICT)
                    → tâches assignées : désassignées    (SET NULL, DB seule)
DELETE organization → 409 si contient des projets        (service + RESTRICT)
DELETE project      → tâches supprimées                  (CASCADE, DB seule)
                      └→ commentaires supprimés          (CASCADE transitif)
DELETE task         → commentaires supprimés             (CASCADE, DB seule)
DELETE comment      → aucune dépendance
```

## Schémas Pydantic (par domaine, 4 classes, ordre alphabétique)

Patron uniforme dans chaque `schemas.py` — illustration users :

| Classe | Rôle | Particularités |
|---|---|---|
| `UserBase` | champs communs | `email: EmailStr`, `full_name: str`, `role: UserRole` |
| `UserCreate` | corps de POST | hérite de Base + `password: str` (min 8) — jamais dans Read |
| `UserRead` | réponse API | Base + `id`, `created_at`, `updated_at` ; `model_config = ConfigDict(from_attributes=True)` ; **jamais** `hashed_password` |
| `UserUpdate` | corps de PATCH | tous champs `Optional`, défaut `None` (dont `password`) |

Déclinaisons : `OrganizationCreate` porte `owner_id: int` ;
`ProjectCreate` porte `organization_id: int` ; `TaskCreate` porte
`project_id: int` et `assignee_id: int | None` ; `CommentCreate` porte
`task_id: int` et `author_id: int`. Les `*Update` n'autorisent jamais le
changement de parent structurel (`organization_id`, `project_id`,
`task_id`, `author_id`, `owner_id` absents des Update). Seul `assignee_id`
reste modifiable sur `TaskUpdate` : les services appliquent les PATCH via
`model_dump(exclude_unset=True)`, donc `"assignee_id": null` explicitement
fourni désassigne, tandis qu'un champ absent ne change rien.

Contrainte de longueur : `Field(max_length=...)` aligné sur les colonnes
(`email` 255, `full_name` 100, `name` 100, `title` 200).

## Clés naturelles du seed (D11)

`users.email` → `organizations.name` → `projects(organization, name)` →
`tasks(project, title)` → `comments(task, author, content)`.
