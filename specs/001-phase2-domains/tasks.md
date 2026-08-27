# Tasks: Phase 2 — Domaines métier

**Input**: Design documents from `/specs/001-phase2-domains/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/api.md](contracts/api.md), [quickstart.md](quickstart.md)

**Tests**: Inclus — exigés par FR-024 (unit sans DB, intégration contre PostgreSQL réel, jamais SQLite).

**Organization**: groupement par **jalon** (4 → 9), ordre strictement séquentiel (SC-006).
Un jalon = une user story : US1=users, US2=organizations, US3=projects, US4=tasks,
US5=comments, US6=seed. Aucune tâche de phase 3 (pas de scripts AST, pas
d'en-têtes `[RAG]`/`[MODEL]`/`[SCHEMA]` — reportés, cf. plan Constitution Check).

## Format: `[ID] [P?] [Story] Description`

- **[P]** : parallélisable (fichiers différents, aucune dépendance entre elles)
- **[Story]** : user story de rattachement (US1–US6)
- Chemins de fichiers exacts dans chaque description

## Conventions transversales (rappel, applicables à toutes les tâches de code)

- Standard Alpha-Scope V3 intégral sur `services.py` / `router.py` : zones A/B/C,
  docstrings de règles métier (jamais une paraphrase du nom), bloc
  `─── ZONE DE DÉCLARATION DES VARIABLES ───`, étapes `[STEP n]` avec
  postcondition `→`, 25–30 lignes max par fonction, **tri alphabétique strict**
  des fonctions. Marqueurs `[FILE]` et `[CODE_START]` sur tous les fichiers.
- `db: AsyncSession` toujours **premier argument** des services ; arguments
  suivants triés alphabétiquement. Sessions via `get_db` exclusivement.
- Migrations **uniquement** via `make db-revision m="..."` (jamais
  `alembic revision` à la main).
- Imports inter-domaines : uniquement les `models.py` référencés par FK, dans
  le sens de la FK (D8).

---

## Jalon 4 — users : LE GABARIT (US1, P1) 🎯 MVP

**Goal** : domaine `users` complet (5 endpoints CRUD), qui calibre le patron
répliqué par les jalons 5–8. Inclut le préambule unique de la phase
(naming convention, dépendances, conftest).

**Independent Test** : cycle CRUD complet sur `/api/v1/users` sans qu'aucun
autre domaine n'existe (spec US1).

### Préambule du jalon (une seule fois)

- [x] T001 [US1] **Retouche naming convention — OBLIGATOIREMENT AVANT la première migration** : dans `app/core/database.py`, ajouter `NAMING_CONVENTION: dict[str, str]` (patrons ix/uq/ck/fk/pk exacts de research.md D3) et faire porter `metadata = MetaData(naming_convention=NAMING_CONVENTION)` par `Base`. Aucune autre modification de la fondation.
- [x] T002 [P] [US1] Dépendances et config test dans `pyproject.toml` : `bcrypt = "^5.0"` (principal), `pydantic` → `{ extras = ["email"], version = "^2.11.0" }`, `httpx = "^0.28"` (groupe dev), `asyncio_default_fixture_loop_scope = "session"` dans `[tool.pytest.ini_options]` ; puis `poetry lock && poetry install` (D5, D6, D10, D13).

### Implémentation du domaine

- [x] T003 [P] [US1] Créer `app/domains/users/__init__.py` (vide) et `app/domains/users/models.py` : enum `UserRole(str, Enum)` {admin, member}, classe `User` — colonnes dans l'ordre `id`, puis métier par ordre alphabétique (`email` VARCHAR(255) UNIQUE, `full_name` VARCHAR(100), `hashed_password` VARCHAR(255), `role` VARCHAR(20) défaut `member`), puis `created_at`/`updated_at` TIMESTAMPTZ `server_default=func.now()` ; `__table_args__` : CHECK nommé `role IN ('admin','member')`. Style `Mapped[...]`/`mapped_column`, pas de `relationship()` (data-model.md, D1, D4, D12).
- [x] T004 [P] [US1] Créer `app/domains/users/schemas.py` : 4 classes en ordre alphabétique `UserBase` (email `EmailStr`, full_name, role), `UserCreate` (Base + `password` min 8), `UserRead` (Base + id, created_at, updated_at ; `model_config = ConfigDict(from_attributes=True)` ; **jamais** de champ mot de passe), `UserUpdate` (tout `Optional`, défaut `None`). `Field(max_length=...)` aligné sur les colonnes. Données pures, aucune méthode (data-model.md).
- [x] T005 [US1] Créer `app/domains/users/services.py` (dépend de T003, T004) : `_hash_password(password: str) -> str` (bcrypt, préfixe `_` le trie en tête), puis `create_user`, `delete_user`, `get_user`, `list_users`, `update_user` — signatures exactes du plan §4.3. Règles : unicité email par SELECT préalable → 409 `"Email already registered"` (create + update) ; 404 `"User {id} not found"` sur id inconnu ; `update_user` en `model_dump(exclude_unset=True)` ; **`delete_user` = DELETE simple** (les vérifications 409 arrivent aux jalons 5 et 8 — seule retouche inter-jalons autorisée) ; `await db.commit()` puis `await db.refresh(...)`, une écriture par requête (D2, D5, D7).
- [x] T006 [US1] Créer `app/domains/users/router.py` (dépend de T005) : `router = APIRouter(prefix="/users", tags=["users"])`, 5 handlers homonymes des services, tri alphabétique, `db: AsyncSession = Depends(get_db)`, wrappers minces sans logique. Statuts 201/204/200/200/200, `response_model=UserRead` / `list[UserRead]`, pagination `limit: int = Query(default=50, ge=1, le=100)`, `offset: int = Query(default=0, ge=0)` (contracts/api.md, D9).
- [x] T007 [US1] Monter le routeur dans `app/main.py` [STEP 2] : `app.include_router(users_router, prefix="/api/v1")`.

### Tests

- [x] T008 [US1] Créer `tests/conftest.py` (D10) : `db_engine` (scope session — DSN dérivé de `settings.database_url` avec base `alpha_scope_test`, création de la base si absente via connexion AUTOCOMMIT sur `postgres`, `drop_all` + `create_all` de `Base.metadata`, dispose final) ; `db_session` (scope function) ; `client` (`httpx.AsyncClient` + `ASGITransport` sur `create_app()`, `dependency_overrides[get_db]`, lifespan non exécuté) ; fixture autouse `TRUNCATE <toutes les tables> RESTART IDENTITY CASCADE` après chaque test.
- [x] T009 [P] [US1] Créer `tests/unit/test_users_schemas.py` (sans DB) : payload valide accepté, email invalide rejeté, rôle hors enum rejeté, mot de passe < 8 rejeté, `UserUpdate()` vide valide, longueurs max respectées.
- [x] T010 [P] [US1] Créer `tests/integration/test_users_router.py` (une fonction par scénario) : create 201 sans champ mot de passe dans la réponse, doublon email 409, get 200/404, list + pagination (défauts, bornes, 422), patch partiel 200 / 404 / email dupliqué 409, delete 204 puis get 404, delete id inconnu 404 (spec US1, contracts/api.md).

### Migration et gate

- [x] T011 [US1] Dans `alembic/env.py`, décommenter/ajouter `from app.domains.users import models as users_models  # noqa: F401`.
- [x] T012 [US1] **GATE jalon 4** (quickstart.md, dans cet ordre, tout vert) : `make db-revision m="users_domain"` → `make db-migrate` → `poetry run pytest` → `poetry run mypy app alembic tests` → `poetry run ruff check app alembic tests && poetry run ruff format --check app alembic tests`.

**Checkpoint** : gabarit validé — `users` fonctionne seul, patron calibré pour les jalons 5–8.

---

## Jalon 5 — organizations (US2, P2)

**Goal** : première relation inter-domaines (`owner_id → users.id`,
`ondelete=RESTRICT`) ; `delete_user` gagne sa première vérification 409.

**Independent Test** : CRUD complet sur `/api/v1/organizations` avec refus
d'un propriétaire inexistant (spec US2).

### Implémentation (déclinaison du gabarit T003–T007)

- [x] T013 [P] [US2] Créer `app/domains/organizations/__init__.py` et `models.py` : classe `Organization` — `id`, `name` VARCHAR(100) UNIQUE, `owner_id` INTEGER NOT NULL FK → `users.id` `ondelete="RESTRICT"` `index=True`, `created_at`/`updated_at` (data-model.md).
- [x] T014 [P] [US2] Créer `app/domains/organizations/schemas.py` : `OrganizationBase` (name), `OrganizationCreate` (Base + `owner_id: int`), `OrganizationRead`, `OrganizationUpdate` = `{name?}` — owner non modifiable (data-model.md).
- [x] T015 [US2] Créer `app/domains/organizations/services.py` : 5 fonctions du patron ; `create_organization` vérifie l'existence de l'owner par SELECT sur `User` (import de `app.domains.users.models` — sens de la FK, D8) → 404 `"User {id} not found"`, et l'unicité du nom → 409 `"Organization name already taken"` ; `delete_organization` = DELETE simple (la vérification « contient des projets » arrive au jalon 6) (plan jalon 5, D2, D7).
- [x] T016 [US2] Créer `app/domains/organizations/router.py` (5 handlers, patron T006) et monter le routeur dans `app/main.py` [STEP 2].

### Retouche inter-jalons

- [x] T017 [US2] **Retouche `delete_user`** dans `app/domains/users/services.py` : ajouter la vérification 409 `"User {id} still owns organizations"` (SELECT sur `Organization` avant DELETE — D2) ; mettre à jour docstring Zone A et étapes `[STEP]` Zone C en conséquence.
- [x] T018 [US2] **Re-exécution des tests des domaines antérieurs** (immédiatement après T017) : `poetry run pytest tests/unit/test_users_schemas.py tests/integration/test_users_router.py` — zéro régression sur le jalon 4.

### Tests

- [x] T019 [P] [US2] Créer `tests/unit/test_organizations_schemas.py` : patron du gabarit (payload valide, `owner_id` requis sur Create, `OrganizationUpdate()` vide valide, longueur max name).
- [x] T020 [P] [US2] Créer `tests/integration/test_organizations_router.py` : patron complet du gabarit (T010) + owner inexistant → 404 ; suppression de l'owner d'une organisation → 409 (spec US2, quickstart jalon 5).

### Migration et gate

- [x] T021 [US2] Dans `alembic/env.py`, ajouter `from app.domains.organizations import models as organizations_models  # noqa: F401`.
- [x] T022 [US2] **GATE jalon 5** : `make db-revision m="organizations_domain"` → `make db-migrate` → `poetry run pytest` → `poetry run mypy app alembic tests` → `poetry run ruff check app alembic tests && poetry run ruff format --check app alembic tests`.

**Checkpoint** : patron d'intégrité référentielle validé — réplicable sur les domaines suivants.

---

## Jalon 6 — projects (US3, P3)

**Goal** : domaine central, unicité composée `(organization_id, name)` ;
`delete_organization` gagne sa vérification 409.

**Independent Test** : CRUD complet sur `/api/v1/projects` avec refus d'une
organisation inexistante (spec US3).

### Implémentation

- [x] T023 [P] [US3] Créer `app/domains/projects/__init__.py` et `models.py` : classe `Project` — `id`, `description` TEXT NOT NULL défaut `''`, `name` VARCHAR(100), `organization_id` INTEGER NOT NULL FK → `organizations.id` `ondelete="RESTRICT"` `index=True`, horodatages ; `__table_args__` : UNIQUE `(organization_id, name)` (data-model.md, D14).
- [x] T024 [P] [US3] Créer `app/domains/projects/schemas.py` : `ProjectBase` (description, name), `ProjectCreate` (Base + `organization_id: int`), `ProjectRead`, `ProjectUpdate` = `{name?, description?}` — organisation non modifiable.
- [x] T025 [US3] Créer `app/domains/projects/services.py` : `create_project` vérifie l'organisation (import `app.domains.organizations.models`, D8) → 404, et l'unicité du nom **dans l'org** → 409 `"Project name already taken in this organization"` (create + update) ; `delete_project` = DELETE simple — la cascade vers les tâches est du ressort de la DB (jalon 7) (plan jalon 6, D2, D7).
- [x] T026 [US3] Créer `app/domains/projects/router.py` (5 handlers, patron T006) et monter le routeur dans `app/main.py` [STEP 2].

### Retouche inter-jalons

- [x] T027 [US3] **Retouche `delete_organization`** dans `app/domains/organizations/services.py` : ajouter la vérification 409 `"Organization {id} still has projects"` (SELECT sur `Project` avant DELETE — D2) ; mettre à jour docstring Zone A et `[STEP]` Zone C.
- [x] T028 [US3] **Re-exécution des tests des domaines antérieurs** (immédiatement après T027) : `poetry run pytest tests/unit/test_users_schemas.py tests/unit/test_organizations_schemas.py tests/integration/test_users_router.py tests/integration/test_organizations_router.py` — zéro régression sur les jalons 4–5.

### Tests

- [x] T029 [P] [US3] Créer `tests/unit/test_projects_schemas.py` : patron du gabarit (+ `description` défaut, `organization_id` requis sur Create).
- [x] T030 [P] [US3] Créer `tests/integration/test_projects_router.py` : patron complet + org inexistante → 404 ; doublon de nom dans la même org → 409 ; même nom dans une autre org → 201 ; suppression de l'org occupée → 409 (spec US3, quickstart jalon 6).

### Migration et gate

- [x] T031 [US3] Dans `alembic/env.py`, ajouter `from app.domains.projects import models as projects_models  # noqa: F401`.
- [x] T032 [US3] **GATE jalon 6** : `make db-revision m="projects_domain"` → `make db-migrate` → `poetry run pytest` → `poetry run mypy app alembic tests` → `poetry run ruff check app alembic tests && poetry run ruff format --check app alembic tests`.

**Checkpoint** : chaîne users → organizations → projects complète et bloquante à la suppression.

---

## Jalon 7 — tasks (US4, P4)

**Goal** : première double référence inter-domaines, enums `TaskStatus` /
`TaskPriority`, assignation optionnelle et révocable. Aucune retouche
inter-jalons dans ce jalon (`delete_user` vs assignation = SET NULL, DB seule, D2).

**Independent Test** : CRUD complet sur `/api/v1/tasks`, transitions de statut,
assignation/désassignation (spec US4).

### Implémentation

- [x] T033 [P] [US4] Créer `app/domains/tasks/__init__.py` et `models.py` : enums `TaskStatus(str, Enum)` {todo, in_progress, done} et `TaskPriority(str, Enum)` {low, medium, high} ; classe `Task` — `id`, `assignee_id` INTEGER **NULLABLE** FK → `users.id` `ondelete="SET NULL"` `index=True`, `description` TEXT défaut `''`, `priority` VARCHAR(20) défaut `medium`, `project_id` INTEGER NOT NULL FK → `projects.id` `ondelete="CASCADE"` `index=True`, `status` VARCHAR(20) défaut `todo`, `title` VARCHAR(200), horodatages ; `__table_args__` : deux CHECK nommés (status, priority) (data-model.md, D1).
- [x] T034 [P] [US4] Créer `app/domains/tasks/schemas.py` : `TaskBase` (description, priority, status, title), `TaskCreate` (Base + `project_id: int`, `assignee_id: int | None`), `TaskRead`, `TaskUpdate` = `{title?, description?, status?, priority?, assignee_id?}` — projet non modifiable ; seul parent modifiable de la phase : `assignee_id`.
- [x] T035 [US4] Créer `app/domains/tasks/services.py` : `create_task` vérifie le projet → 404 et, si fourni, l'assigné → 404 (imports `projects.models` + `users.models`, D8) ; `update_task` vérifie l'assigné si présent dans le payload ; sémantique `exclude_unset` — `"assignee_id": null` explicite désassigne, champ absent ne change rien ; `delete_task` = DELETE simple, cascade commentaires par la DB (plan jalon 7, D2, D7).
- [x] T036 [US4] Créer `app/domains/tasks/router.py` (5 handlers, patron T006) et monter le routeur dans `app/main.py` [STEP 2].

### Tests

- [x] T037 [P] [US4] Créer `tests/unit/test_tasks_schemas.py` : patron + status/priority hors enum rejetés, `assignee_id` optionnel sur Create, distinction champ absent / `null` explicite sur `TaskUpdate`.
- [x] T038 [P] [US4] Créer `tests/integration/test_tasks_router.py` : patron complet + création non assignée 201 ; projet ou assigné inexistant → 404 ; enum invalide → 422 ; assignation puis désassignation via PATCH (`"assignee_id": null`) ; suppression du projet → tâches disparues (cascade DB) ; suppression de l'assigné → 204, tâche conservée avec `assignee_id: null` (spec US4, quickstart jalon 7).

### Migration et gate

- [x] T039 [US4] Dans `alembic/env.py`, ajouter `from app.domains.tasks import models as tasks_models  # noqa: F401`.
- [x] T040 [US4] **GATE jalon 7** : `make db-revision m="tasks_domain"` → `make db-migrate` → `poetry run pytest` → `poetry run mypy app alembic tests` → `poetry run ruff check app alembic tests && poetry run ruff format --check app alembic tests`.

**Checkpoint** : ensembles fermés et référence optionnelle validés ; axe de contenance projects → tasks en place.

---

## Jalon 8 — comments (US5, P5)

**Goal** : dernier maillon du graphe (relation la plus imbriquée) ;
`delete_user` atteint sa **forme finale**.

**Independent Test** : CRUD complet sur les commentaires d'une tâche, refus de
tâche ou d'auteur inexistants (spec US5).

### Implémentation

- [x] T041 [P] [US5] Créer `app/domains/comments/__init__.py` et `models.py` : classe `Comment` — `id`, `author_id` INTEGER NOT NULL FK → `users.id` `ondelete="RESTRICT"` `index=True`, `content` TEXT NOT NULL, `task_id` INTEGER NOT NULL FK → `tasks.id` `ondelete="CASCADE"` `index=True`, horodatages (data-model.md).
- [x] T042 [P] [US5] Créer `app/domains/comments/schemas.py` : `CommentBase` (content), `CommentCreate` (Base + `author_id: int`, `task_id: int`), `CommentRead`, `CommentUpdate` = `{content?}` — tâche et auteur non modifiables.
- [x] T043 [US5] Créer `app/domains/comments/services.py` : `create_comment` vérifie tâche et auteur → 404 (imports `tasks.models` + `users.models`, D8) ; `list_comments(db, limit, offset, task_id)` **exige** `task_id` et vérifie son existence → 404 ; `delete_comment` = DELETE simple, aucune dépendance (plan jalon 8, D7).
- [x] T044 [US5] Créer `app/domains/comments/router.py` : 5 handlers du patron, avec `task_id: int = Query(...)` **obligatoire** sur `list_comments` (FR-021, 422 si absent) ; monter le routeur dans `app/main.py` [STEP 2].

### Retouche inter-jalons

- [x] T045 [US5] **Retouche `delete_user`** dans `app/domains/users/services.py` : ajouter la vérification 409 `"User {id} still has comments"` (SELECT sur `Comment` avant DELETE — D2). La fonction atteint sa **forme finale** ; docstring Zone A et `[STEP]` Zone C mis à jour.
- [x] T046 [US5] **Re-exécution des tests des domaines antérieurs** (immédiatement après T045) : `poetry run pytest tests/unit/test_users_schemas.py tests/unit/test_organizations_schemas.py tests/unit/test_projects_schemas.py tests/unit/test_tasks_schemas.py tests/integration/test_users_router.py tests/integration/test_organizations_router.py tests/integration/test_projects_router.py tests/integration/test_tasks_router.py` — zéro régression sur les jalons 4–7.

### Tests

- [x] T047 [P] [US5] Créer `tests/unit/test_comments_schemas.py` : patron du gabarit (`task_id`/`author_id` requis sur Create, `CommentUpdate()` vide valide).
- [x] T048 [P] [US5] Créer `tests/integration/test_comments_router.py` : patron complet + liste filtrée par tâche (et uniquement elle) ; `GET /api/v1/comments` sans `task_id` → 422 ; tâche ou auteur inexistant → 404 ; suppression de la tâche → commentaires disparus ; suppression d'un auteur → 409 ; chaîne complète de cascade projet → tâches → commentaires (spec US5, quickstart jalon 8).

### Migration et gate

- [x] T049 [US5] Dans `alembic/env.py`, ajouter `from app.domains.comments import models as comments_models  # noqa: F401`.
- [x] T050 [US5] **GATE jalon 8** : `make db-revision m="comments_domain"` → `make db-migrate` → `poetry run pytest` → `poetry run mypy app alembic tests` → `poetry run ruff check app alembic tests && poetry run ruff format --check app alembic tests`.

**Checkpoint** : graphe relationnel complet (25 endpoints), politique de suppression double couche intégrale.

---

## Jalon 9 — Seed idempotent (US6, P6)

**Goal** : peuplement de démonstration en une commande, relançable N fois sans
doublon ni divergence (SC-004).

**Independent Test** : `make db-seed` deux fois sur base vide → état final
strictement identique (spec US6).

### Implémentation

- [x] T051 [US6] Créer `app/scripts/seed.py` (Alpha-Scope V3 intégral) : jeu de données constant au niveau module ; get-or-create par clé naturelle (D11 : `users.email` → `organizations.name` → `projects(organization_id, name)` → `tasks(project_id, title)` → `comments(task_id, author_id, content)`) dans l'ordre users → organizations → projects → tasks → comments ; moteur via `init_db_engine()` + `async_session_factory` (jamais de session à la main) ; exécutable `python -m app.scripts.seed`. Couverture obligatoire : les 6 arêtes FK, 2 rôles, 3 statuts, 3 priorités, tâches assignées et non assignées, ≥2 commentaires sur une même tâche. Volumes indicatifs : 5 users, 2 orgs, 4 projects, 12 tasks, 8 comments (plan jalon 9).
- [x] T052 [US6] Dans le `Makefile`, remplacer l'écho de la cible `db-seed` par `poetry run python -m app.scripts.seed`.

### Tests

- [x] T053 [P] [US6] Créer `tests/unit/test_seed.py` : helpers purs éventuels du module seed (sans DB).
- [x] T054 [P] [US6] Créer `tests/integration/test_seed_idempotence.py` : exécuter le seed deux fois dans la base de test ; comparer les comptes de lignes et l'ensemble des clés naturelles (identiques) ; vérifier la couverture (6 arêtes FK, enums complets) (spec US6, SC-004).

### Gate

- [x] T055 [US6] **GATE jalon 9** (gate uniforme du quickstart) : `make db-revision m="seed_noop_check"` — sert ici de **contrôle de dérive** : le seed ne change pas le schéma, donc autogenerate ne doit rien détecter (une migration non vide = bug à corriger avant clôture, une révision vide générée est supprimée) → `make db-migrate` → `poetry run pytest` → `poetry run mypy app alembic tests` → `poetry run ruff check app alembic tests && poetry run ruff format --check app alembic tests`.

**Checkpoint final** : Phase 2 close — 25 endpoints, 5 migrations de domaines empilées sur la baseline `f2476b2dee09`, `make db-seed` idempotent, qualité 100 % verte.

---

## Dependencies & Execution Order

### Ordre des jalons (strict, SC-006)

- **Jalon 4 (T001–T012)** → **Jalon 5 (T013–T022)** → **Jalon 6 (T023–T032)** → **Jalon 7 (T033–T040)** → **Jalon 8 (T041–T050)** → **Jalon 9 (T051–T055)**.
- Un jalon ne s'ouvre que lorsque le gate du précédent est intégralement vert.
- Chaque gate (T012, T022, T032, T040, T050, T055) est **le dernier** de son jalon.

### Dépendances structurantes

- **T001 (naming convention) précède T012** — première génération de migration : sans elle, les CHECK de D1 et l'autogenerate produisent des contraintes non nommées, non déterministes (D3).
- Dans chaque jalon : models + schemas ([P] entre eux) → services → router/montage → tests → import `env.py` → gate.
- **T008 (conftest)** requis avant tout test d'intégration (T010, T020, T030, T038, T048, T054).
- Chaque retouche inter-jalons est suivie **immédiatement** de sa re-exécution de tests : T017→T018, T027→T028, T045→T046.
- T051 (seed) requiert les 5 domaines migrés (post-T050) ; T054 requiert T051 + T052.

### Parallel Opportunities

- Au sein d'un jalon uniquement (jamais entre jalons) : `models.py` ∥ `schemas.py` (ex. T003 ∥ T004), tests unit ∥ tests integration (ex. T009 ∥ T010), T002 ∥ T001.
- Exemple jalon 7 : lancer T033 et T034 ensemble ; après T036, lancer T037 et T038 ensemble.

---

## Implementation Strategy

- **MVP = jalon 4** : premier passage complet du cycle domaine + tests +
  migration + gate ; il calibre le gabarit — toute correction de patron doit se
  faire ici, pas en aval.
- **Livraison incrémentale** : chaque jalon laisse l'API dans un état
  démontrable (quickstart § validation fonctionnelle par jalon).
- **Hors périmètre** : aucune tâche de phase 3 — pas de
  `generate_topology_headers.py`, pas de `generate_structural_metadata.py`,
  aucun en-tête `[RAG]`/`[MODEL]`/`[SCHEMA]` écrit à la main (CLAUDE.md §6–7).

## Notes

- [P] = fichiers différents, aucune dépendance mutuelle, même jalon.
- Les retouches T017, T027, T045 sont les **seules** modifications autorisées
  de code livré par un jalon antérieur (plan, Complexity Tracking).
- Total : 55 tâches — J4 : 12 · J5 : 10 · J6 : 10 · J7 : 8 · J8 : 10 · J9 : 5.
