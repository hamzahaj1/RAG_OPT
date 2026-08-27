# CONTRACTS — Contrats inter-domaines Alpha-Scope

> Documentation de référence des **6 arêtes FK cross-domaines** du graphe
> relationnel (CLAUDE.md §3), établie au jalon 12 depuis les sources de
> vérité exclusives : migrations Alembic (noms de contraintes réels),
> docstrings des services (codes et messages exacts), blocs `[MODEL]`
> générés. Aucune règle n'est énoncée ici qui ne figure dans une source.
>
> Ce document appartient au **corpus RAG indexable** (arbitrage jalon 12,
> CLAUDE.md §4 bis) : **une section d'arête = un chunk**.

## Principe transversal — la double couche (D2)

Chaque arête est défendue deux fois :

- **Couche applicative** : un SELECT de vérification avant toute
  écriture, dans le service — `404 Not Found` au format commun
  « `Entity {id} not found` » (FR-003) quand la cible référencée
  n'existe pas à la création ; `409 Conflict` nommé quand une
  suppression amont est bloquée par des lignes aval.
- **Couche DB (backstop)** : la contrainte FK nommée (convention
  `fk_<table>_<colonne>_<table_cible>`, D3), qui garantit l'invariant
  même si la couche applicative était contournée.

**Dérogation actée** (plan phase 2, jalon 7) : l'arête d'assignation
(`tasks.assignee_id`, `SET NULL`) est portée par la **DB seule** en
suppression — première et unique dérogation au patron 409.

Vue d'ensemble (data-model.md, § Sémantique de suppression) :

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

---

## Arête 1 — `organizations.owner_id` → `users.id`

| Attribut | Valeur |
|---|---|
| Politique | **RESTRICT** |
| Contrainte | `fk_organizations_owner_id_users` (`ondelete=RESTRICT`) |
| Index | `ix_organizations_owner_id` |
| Nullabilité | NOT NULL |
| Migration | `1d70e9de6246` (organizations_domain) |

**Double couche de vérification** :

- *Création* — `create_organization` vérifie l'existence du propriétaire
  par SELECT sur `users` avant toute écriture → `404` « `User {id} not
  found` » (FR-011, D2).
- *Suppression amont* — `delete_user` refuse un propriétaire
  d'organisations par SELECT applicatif → `409` « `User {id} still owns
  organizations` » ; **backstop** : la FK `RESTRICT`.

**Invariants métier** (docstrings `organizations/services.py`) :

- Toute organisation a exactement un propriétaire existant — aucune FK
  orpheline ne peut être écrite.
- Le propriétaire n'est **jamais modifiable** après création
  (`OrganizationUpdate` n'expose pas `owner_id` — Phase 2).

---

## Arête 2 — `projects.organization_id` → `organizations.id`

| Attribut | Valeur |
|---|---|
| Politique | **RESTRICT** |
| Contrainte | `fk_projects_organization_id_organizations` (`ondelete=RESTRICT`) |
| Index | `ix_projects_organization_id` |
| Nullabilité | NOT NULL |
| Migration | `677e300dd994` (projects_domain) ; unicité composée renommée `uq_projects_organization_id_name` par `a48ad14da82b` |

**Double couche de vérification** :

- *Création* — `create_project` vérifie l'existence de l'organisation
  par SELECT avant toute écriture → `404` « `Organization {id} not
  found` » ; l'unicité du nom **dans l'organisation** est refusée en
  `409` « `Project name already taken in this organization` »
  (contrainte composée `uq_projects_organization_id_name` en backstop).
- *Suppression amont* — `delete_organization` refuse une organisation
  contenant au moins un projet par SELECT applicatif → `409`
  « `Organization {id} still has projects` » ; **backstop** : la FK
  `RESTRICT`. La suppression est bloquée par les projets, jamais
  propagée vers eux.

**Invariants métier** (docstrings `projects/services.py`) :

- Le rattachement à l'organisation n'est **jamais modifiable**
  (`ProjectUpdate` n'expose pas `organization_id` — Phase 2).
- Le même nom de projet peut exister dans deux organisations distinctes ;
  jamais deux fois dans la même (unicité composée).
- Avec l'arête 1, la **chaîne bloquante amont est complète** :
  users ← organizations ← projects — chaque suppression amont est
  refusée en 409 tant qu'une ligne aval la référence.

---

## Arête 3 — `tasks.project_id` → `projects.id`

| Attribut | Valeur |
|---|---|
| Politique | **CASCADE** (axe de contenance) |
| Contrainte | `fk_tasks_project_id_projects` (`ondelete=CASCADE`) |
| Index | `ix_tasks_project_id` |
| Nullabilité | NOT NULL |
| Migration | `443e75f588d9` (tasks_domain) — premier `CASCADE` du projet |

**Double couche de vérification** :

- *Création* — `create_task` vérifie l'existence du projet par SELECT
  avant toute écriture → `404` « `Project {id} not found` » (D2).
- *Suppression* — la cascade est **portée par la DB seule**
  (`delete_project` : « jamais par un SELECT applicatif ») : la
  suppression du projet emporte ses tâches, puis leurs commentaires
  (cascade transitive via l'arête 5) — vérifiée par le premier test à
  trois niveaux du projet (DELETE projet → tâche 404 **et**
  commentaire 404, jalon 8).

**Invariants métier** (docstrings `tasks/models.py`, `tasks/services.py`) :

- La suppression du projet emporte la tâche, **jamais l'inverse** : la
  tâche vivante retient son `project_id` (tests bidirectionnels,
  jalon 7).
- Le rattachement au projet n'est **jamais modifiable** (`TaskUpdate`
  n'expose pas `project_id` — Phase 2).

---

## Arête 4 — `tasks.assignee_id` → `users.id`

| Attribut | Valeur |
|---|---|
| Politique | **SET NULL** (axe de référence, détachement) |
| Contrainte | `fk_tasks_assignee_id_users` (`ondelete=SET NULL`) |
| Index | `ix_tasks_assignee_id` |
| Nullabilité | **NULLABLE** — seule FK nullable de la phase 2 |
| Migration | `443e75f588d9` (tasks_domain) — premier `SET NULL` du projet |

**Double couche de vérification** :

- *Création* — l'assigné est optionnel ; s'il est fourni, il doit
  exister → `404` « `User {id} not found` » ; une tâche naît non
  assignée quand `assignee_id` est absent ou `null`.
- *Suppression* — **DB seule, dérogation actée au patron 409** (plan
  phase 2, jalon 7) : la suppression de l'assigné répond `204`, la
  tâche **subsiste** avec `assignee_id: null` — l'assignation ne bloque
  jamais la suppression d'un utilisateur.

**Invariants métier** (docstrings `tasks/models.py`, `update_task`) :

- `NULL` signifie « non assignée ».
- `update_task` distingue **trois cas** (sémantique `exclude_unset`) :
  champ absent → pas de changement ; `null` explicite → désassignation
  applicative ; entier → assignation, l'assigné doit exister (`404`
  « `User {id} not found` »).

---

## Arête 5 — `comments.task_id` → `tasks.id`

| Attribut | Valeur |
|---|---|
| Politique | **CASCADE** (axe de contenance) |
| Contrainte | `fk_comments_task_id_tasks` (`ondelete=CASCADE`) |
| Index | `ix_comments_task_id` |
| Nullabilité | NOT NULL |
| Migration | `3b55d9e3f2bf` (comments_domain) |

**Double couche de vérification** :

- *Création* — `create_comment` vérifie l'existence de la tâche par
  SELECT avant toute écriture → `404` « `Task {id} not found` » (D2).
- *Suppression* — cascade **portée par la DB seule** (`delete_task` :
  « jamais par un SELECT applicatif ») : la suppression de la tâche
  emporte ses commentaires ; ce même chemin est le second étage de la
  cascade transitive projects → tasks → comments (arête 3).

**Invariants métier** (docstrings `comments/services.py`) :

- La tâche est **fixée à la création** — non modifiable ensuite
  (`CommentUpdate` n'expose pas `task_id` — Phase 2).
- **Jamais de liste globale de commentaires** (FR-021) :
  `GET /api/v1/comments` exige `task_id` en paramètre de requête —
  `422` sans lui (validation du routeur), `404` « `Task {id} not
  found` » si la tâche est inconnue.

---

## Arête 6 — `comments.author_id` → `users.id`

| Attribut | Valeur |
|---|---|
| Politique | **RESTRICT** |
| Contrainte | `fk_comments_author_id_users` (`ondelete=RESTRICT`) |
| Index | `ix_comments_author_id` |
| Nullabilité | NOT NULL |
| Migration | `3b55d9e3f2bf` (comments_domain) |

**Double couche de vérification** :

- *Création* — `create_comment` vérifie l'existence de l'auteur par
  SELECT sur `users` avant toute écriture → `404` « `User {id} not
  found` » (D2).
- *Suppression amont* — `delete_user` refuse un auteur de commentaires
  par SELECT applicatif → `409` « `User {id} still has comments` » ;
  **backstop** : la FK `RESTRICT`. Vérifié dans les deux sens au
  jalon 8 : le 409 laisse le user **et** ses commentaires intacts.

**Invariants métier** (docstrings `comments/services.py`,
`users/services.py`) :

- L'auteur est **fixé à la création** — non modifiable ensuite
  (Phase 2) : l'attribution des commentaires reste intègre.
- Avec les arêtes 1 et 4, `delete_user` atteint sa **forme finale**
  (jalon 8) : deux blocages 409 (organisations, commentaires) et un
  détachement silencieux (assignation, SET NULL, DB seule).

---

## Sources

| Source | Rôle |
|---|---|
| `alembic/versions/1d70e9de6246_*.py`, `677e300dd994_*.py`, `443e75f588d9_*.py`, `3b55d9e3f2bf_*.py`, `a48ad14da82b_*.py` | noms de contraintes et politiques `ondelete` réels |
| Docstrings de `app/domains/*/services.py` | codes 404/409, messages exacts, invariants |
| Blocs `[MODEL]` de `app/domains/*/models.py` (générés, jalon 11) | `fks` / `referenced_by` par table |
| `specs/001-phase2-domains/data-model.md` | tables, nullabilité, sémantique de suppression |
