# Contrat API REST — Phase 2 : Domaines métier

**Feature**: `001-phase2-domains` | **Date**: 2026-08-27
**Références** : [data-model.md](../data-model.md) pour les champs, [research.md](../research.md) D9.

## Conventions (identiques sur les cinq domaines)

- Préfixe : `/api/v1` (monté dans `create_app`) ; chaque routeur déclare
  son propre `prefix="/<domaine>"` et `tags=["<domaine>"]`.
- 5 endpoints par domaine, un par fonction de service, mêmes noms de
  fonctions dans `router.py` que dans `services.py` (wrapper mince).
- Statuts : `POST` 201 · `GET` 200 · `PATCH` 200 · `DELETE` 204 (corps vide).
- Erreurs (corps FastAPI standard `{"detail": "..."}`) :
  - **404** — id du path introuvable, **ou** référence FK inexistante à
    l'écriture ; le détail nomme l'entité et l'id : `"User 42 not found"`.
  - **409** — violation d'unicité (`"Email already registered"`,
    `"Organization name already taken"`, `"Project name already taken in
    this organization"`) ou suppression bloquée (`"User 3 still owns
    organizations"`, `"User 3 still has comments"`, `"Organization 2
    still has projects"`).
  - **422** — validation Pydantic (formats, longueurs, enums, pagination).
- Pagination sur toutes les listes : `?offset=0&limit=50`
  (`offset ≥ 0`, `1 ≤ limit ≤ 100`), réponse = tableau JSON plat, trié par
  `id` croissant.
- `PATCH` partiel : sémantique `exclude_unset` — seuls les champs
  présents dans le corps sont appliqués.

## users

| Méthode & chemin | Corps | Réponse | Erreurs |
|---|---|---|---|
| `POST /api/v1/users` | `UserCreate` {email, full_name, role, password≥8} | 201 `UserRead` | 409 email pris |
| `DELETE /api/v1/users/{user_id}` | — | 204 | 404 ; 409 possède orgs ou commentaires |
| `GET /api/v1/users/{user_id}` | — | 200 `UserRead` | 404 |
| `GET /api/v1/users` | — | 200 `list[UserRead]` | 422 pagination |
| `PATCH /api/v1/users/{user_id}` | `UserUpdate` (tout optionnel) | 200 `UserRead` | 404 ; 409 email pris |

`UserRead` = {id, email, full_name, role, created_at, updated_at} —
**jamais** de champ mot de passe, en clair ou haché.

## organizations

| Méthode & chemin | Corps | Réponse | Erreurs |
|---|---|---|---|
| `POST /api/v1/organizations` | `OrganizationCreate` {name, owner_id} | 201 `OrganizationRead` | 404 owner inexistant ; 409 nom pris |
| `DELETE /api/v1/organizations/{organization_id}` | — | 204 | 404 ; 409 contient des projets |
| `GET /api/v1/organizations/{organization_id}` | — | 200 | 404 |
| `GET /api/v1/organizations` | — | 200 liste | 422 |
| `PATCH /api/v1/organizations/{organization_id}` | `OrganizationUpdate` {name?} | 200 | 404 ; 409 nom pris |

Le propriétaire (`owner_id`) n'est pas modifiable en phase 2.

## projects

| Méthode & chemin | Corps | Réponse | Erreurs |
|---|---|---|---|
| `POST /api/v1/projects` | `ProjectCreate` {name, description, organization_id} | 201 `ProjectRead` | 404 organisation inexistante ; 409 nom pris dans l'org |
| `DELETE /api/v1/projects/{project_id}` | — | 204 — cascade tâches + commentaires | 404 |
| `GET /api/v1/projects/{project_id}` | — | 200 | 404 |
| `GET /api/v1/projects` | — | 200 liste | 422 |
| `PATCH /api/v1/projects/{project_id}` | `ProjectUpdate` {name?, description?} | 200 | 404 ; 409 nom pris |

## tasks

| Méthode & chemin | Corps | Réponse | Erreurs |
|---|---|---|---|
| `POST /api/v1/tasks` | `TaskCreate` {title, description, status, priority, project_id, assignee_id?} | 201 `TaskRead` | 404 projet ou assigné inexistant ; 422 enum invalide |
| `DELETE /api/v1/tasks/{task_id}` | — | 204 — cascade commentaires | 404 |
| `GET /api/v1/tasks/{task_id}` | — | 200 | 404 |
| `GET /api/v1/tasks` | — | 200 liste | 422 |
| `PATCH /api/v1/tasks/{task_id}` | `TaskUpdate` {title?, description?, status?, priority?, assignee_id?} | 200 | 404 tâche ou assigné ; 422 enum |

`"assignee_id": null` explicitement fourni dans le PATCH désassigne la
tâche ; champ absent = pas de changement.

## comments

| Méthode & chemin | Corps | Réponse | Erreurs |
|---|---|---|---|
| `POST /api/v1/comments` | `CommentCreate` {content, task_id, author_id} | 201 `CommentRead` | 404 tâche ou auteur inexistant |
| `DELETE /api/v1/comments/{comment_id}` | — | 204 | 404 |
| `GET /api/v1/comments/{comment_id}` | — | 200 | 404 |
| `GET /api/v1/comments?task_id={id}` | — | 200 liste des commentaires de la tâche | 404 tâche inexistante ; 422 `task_id` manquant |
| `PATCH /api/v1/comments/{comment_id}` | `CommentUpdate` {content?} | 200 | 404 |

`task_id` est **obligatoire** sur la liste (FR-021) : les commentaires ne
se listent que par tâche.
