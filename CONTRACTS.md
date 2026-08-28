# CONTRACTS — Alpha-Scope cross-domain contracts

> Reference documentation of the **6 cross-domain FK edges** of the
> relational graph (CLAUDE.md §3), established at milestone 12 from the
> exclusive sources of truth: Alembic migrations (real constraint
> names), service docstrings (exact codes and messages), generated
> `[MODEL]` blocks. No rule is stated here that does not appear in a
> source.
>
> This document belongs to the **indexable RAG corpus** (milestone 12
> arbitration, CLAUDE.md §4 bis): **one edge section = one chunk**.

## Cross-cutting principle — the double layer (D2)

Every edge is defended twice:

- **Application layer**: a verification SELECT before any write, in the
  service — `404 Not Found` in the shared format
  "`Entity {id} not found`" (FR-003) when the referenced target does
  not exist at creation; a named `409 Conflict` when an upstream
  deletion is blocked by downstream rows.
- **DB layer (backstop)**: the named FK constraint (convention
  `fk_<table>_<column>_<target_table>`, D3), which guarantees the
  invariant even if the application layer were bypassed.

**Recorded exception** (phase 2 plan, milestone 7): the assignment edge
(`tasks.assignee_id`, `SET NULL`) is carried by the **DB alone** on
deletion — the first and only exception to the 409 pattern.

Overview (data-model.md, § Deletion semantics):

```
DELETE user         → 409 if owner of organizations   (service + RESTRICT)
                    → 409 if author of comments       (service + RESTRICT)
                    → assigned tasks: unassigned      (SET NULL, DB alone)
DELETE organization → 409 if it holds projects        (service + RESTRICT)
DELETE project      → tasks deleted                   (CASCADE, DB alone)
                      └→ comments deleted             (transitive CASCADE)
DELETE task         → comments deleted                (CASCADE, DB alone)
DELETE comment      → no dependency
```

---

## Edge 1 — `organizations.owner_id` → `users.id`

| Attribute | Value |
|---|---|
| Policy | **RESTRICT** |
| Constraint | `fk_organizations_owner_id_users` (`ondelete=RESTRICT`) |
| Index | `ix_organizations_owner_id` |
| Nullability | NOT NULL |
| Migration | `1d70e9de6246` (organizations_domain) |

**Double verification layer**:

- *Creation* — `create_organization` checks the owner's existence by
  SELECT on `users` before any write → `404` "`User {id} not found`"
  (FR-011, D2).
- *Upstream deletion* — `delete_user` refuses an owner of organizations
  by application-level SELECT → `409` "`User {id} still owns
  organizations`"; **backstop**: the `RESTRICT` FK.

**Business invariants** (docstrings `organizations/services.py`):

- Every organization has exactly one existing owner — no orphan FK can
  be written.
- The owner is **never modifiable** after creation
  (`OrganizationUpdate` does not expose `owner_id` — Phase 2).

---

## Edge 2 — `projects.organization_id` → `organizations.id`

| Attribute | Value |
|---|---|
| Policy | **RESTRICT** |
| Constraint | `fk_projects_organization_id_organizations` (`ondelete=RESTRICT`) |
| Index | `ix_projects_organization_id` |
| Nullability | NOT NULL |
| Migration | `677e300dd994` (projects_domain); composite uniqueness renamed `uq_projects_organization_id_name` by `a48ad14da82b` |

**Double verification layer**:

- *Creation* — `create_project` checks the organization's existence by
  SELECT before any write → `404` "`Organization {id} not found`"; name
  uniqueness **within the organization** is refused with `409`
  "`Project name already taken in this organization`" (composite
  constraint `uq_projects_organization_id_name` as backstop).
- *Upstream deletion* — `delete_organization` refuses an organization
  holding at least one project by application-level SELECT → `409`
  "`Organization {id} still has projects`"; **backstop**: the
  `RESTRICT` FK. The deletion is blocked by the projects, never
  propagated to them.

**Business invariants** (docstrings `projects/services.py`):

- The attachment to the organization is **never modifiable**
  (`ProjectUpdate` does not expose `organization_id` — Phase 2).
- The same project name may exist in two distinct organizations; never
  twice in the same one (composite uniqueness).
- Together with edge 1, the **upstream blocking chain is complete**:
  users ← organizations ← projects — every upstream deletion is refused
  with 409 as long as a downstream row references it.

---

## Edge 3 — `tasks.project_id` → `projects.id`

| Attribute | Value |
|---|---|
| Policy | **CASCADE** (containment axis) |
| Constraint | `fk_tasks_project_id_projects` (`ondelete=CASCADE`) |
| Index | `ix_tasks_project_id` |
| Nullability | NOT NULL |
| Migration | `443e75f588d9` (tasks_domain) — the project's first `CASCADE` |

**Double verification layer**:

- *Creation* — `create_task` checks the project's existence by SELECT
  before any write → `404` "`Project {id} not found`" (D2).
- *Deletion* — the cascade is **carried by the DB alone**
  (`delete_project`: "never by an application-level SELECT"): deleting
  the project takes its tasks with it, then their comments (transitive
  cascade through edge 5) — verified by the project's first three-level
  test (DELETE project → task 404 **and** comment 404, milestone 8).

**Business invariants** (docstrings `tasks/models.py`, `tasks/services.py`):

- Deleting the project takes the task with it, **never the reverse**:
  the living task keeps its `project_id` (bidirectional tests,
  milestone 7).
- The attachment to the project is **never modifiable** (`TaskUpdate`
  does not expose `project_id` — Phase 2).

---

## Edge 4 — `tasks.assignee_id` → `users.id`

| Attribute | Value |
|---|---|
| Policy | **SET NULL** (reference axis, detachment) |
| Constraint | `fk_tasks_assignee_id_users` (`ondelete=SET NULL`) |
| Index | `ix_tasks_assignee_id` |
| Nullability | **NULLABLE** — the only nullable FK of phase 2 |
| Migration | `443e75f588d9` (tasks_domain) — the project's first `SET NULL` |

**Double verification layer**:

- *Creation* — the assignee is optional; when provided, it must exist
  → `404` "`User {id} not found`"; a task is born unassigned when
  `assignee_id` is absent or `null`.
- *Deletion* — **DB alone, recorded exception to the 409 pattern**
  (phase 2 plan, milestone 7): deleting the assignee responds `204`,
  the task **survives** with `assignee_id: null` — assignment never
  blocks the deletion of a user.

**Business invariants** (docstrings `tasks/models.py`, `update_task`):

- `NULL` means "unassigned".
- `update_task` distinguishes **three cases** (`exclude_unset`
  semantics): absent field → no change; explicit `null` →
  application-level unassignment; integer → assignment, the assignee
  must exist (`404` "`User {id} not found`").

---

## Edge 5 — `comments.task_id` → `tasks.id`

| Attribute | Value |
|---|---|
| Policy | **CASCADE** (containment axis) |
| Constraint | `fk_comments_task_id_tasks` (`ondelete=CASCADE`) |
| Index | `ix_comments_task_id` |
| Nullability | NOT NULL |
| Migration | `3b55d9e3f2bf` (comments_domain) |

**Double verification layer**:

- *Creation* — `create_comment` checks the task's existence by SELECT
  before any write → `404` "`Task {id} not found`" (D2).
- *Deletion* — cascade **carried by the DB alone** (`delete_task`:
  "never by an application-level SELECT"): deleting the task takes its
  comments with it; this same path is the second stage of the
  transitive cascade projects → tasks → comments (edge 3).

**Business invariants** (docstrings `comments/services.py`):

- The task is **fixed at creation** — not modifiable afterwards
  (`CommentUpdate` does not expose `task_id` — Phase 2).
- **Never a global list of comments** (FR-021):
  `GET /api/v1/comments` requires `task_id` as a query parameter —
  `422` without it (router validation), `404` "`Task {id} not found`"
  when the task is unknown.

---

## Edge 6 — `comments.author_id` → `users.id`

| Attribute | Value |
|---|---|
| Policy | **RESTRICT** |
| Constraint | `fk_comments_author_id_users` (`ondelete=RESTRICT`) |
| Index | `ix_comments_author_id` |
| Nullability | NOT NULL |
| Migration | `3b55d9e3f2bf` (comments_domain) |

**Double verification layer**:

- *Creation* — `create_comment` checks the author's existence by SELECT
  on `users` before any write → `404` "`User {id} not found`" (D2).
- *Upstream deletion* — `delete_user` refuses an author of comments by
  application-level SELECT → `409` "`User {id} still has comments`";
  **backstop**: the `RESTRICT` FK. Verified in both directions at
  milestone 8: the 409 leaves the user **and** their comments intact.

**Business invariants** (docstrings `comments/services.py`,
`users/services.py`):

- The author is **fixed at creation** — not modifiable afterwards
  (Phase 2): comment attribution stays intact.
- Together with edges 1 and 4, `delete_user` reaches its **final form**
  (milestone 8): two 409 blocks (organizations, comments) and one
  silent detachment (assignment, SET NULL, DB alone).

---

## Sources

| Source | Role |
|---|---|
| `alembic/versions/1d70e9de6246_*.py`, `677e300dd994_*.py`, `443e75f588d9_*.py`, `3b55d9e3f2bf_*.py`, `a48ad14da82b_*.py` | real constraint names and `ondelete` policies |
| Docstrings of `app/domains/*/services.py` | 404/409 codes, exact messages, invariants |
| `[MODEL]` blocks of `app/domains/*/models.py` (generated, milestone 11) | `fks` / `referenced_by` per table |
| `specs/001-phase2-domains/data-model.md` | tables, nullability, deletion semantics |
