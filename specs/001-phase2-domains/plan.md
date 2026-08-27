# Implementation Plan: Phase 2 — Domaines métier

**Branch**: `001-phase2-domains` | **Date**: 2026-08-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-phase2-domains/spec.md`

## Summary

Livrer les cinq domaines métier (`users`, `organizations`, `projects`,
`tasks`, `comments`) en six jalons strictement séquentiels (4 → 9), chacun
clos par migration + tests verts + MyPy strict + Ruff. Le **jalon 4
(users) définit le gabarit** — anatomie exacte des 4 fichiers, patron des
fonctions de service et des tests ; les **jalons 5–8 sont des déclinaisons**
dont seules les différences (FK, règles de suppression, champs) sont
spécifiées ; le **jalon 9** livre le seed idempotent. Décisions imposées :
enums Python `(str, Enum)` + String + CHECK (jamais d'ENUM natif PG), et
politique de suppression en double couche — la DB garantit (`ondelete`),
le service explique (`HTTPException` 409). Détail : [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.11+ (local 3.14), typage statique strict obligatoire

**Primary Dependencies**: FastAPI ^0.129, SQLAlchemy 2.0 async + asyncpg ^0.31, Pydantic V2 (+ extra `email`), Alembic ^1.16, bcrypt ^5.0 (nouveau), httpx ^0.28 (dev, nouveau)

**Storage**: PostgreSQL 16 (conteneur podman compose) ; base de test dédiée `alpha_scope_test`

**Testing**: pytest + pytest-asyncio (`asyncio_mode=auto`, `asyncio_default_fixture_loop_scope="session"` à ajouter) ; intégration contre PostgreSQL réel, jamais SQLite

**Target Platform**: Linux, backend conteneurisable (podman compose)

**Project Type**: web-service (backend API ; frontend en phase 4)

**Performance Goals**: N/A pour cette phase — la cible est la régularité structurelle, pas le débit

**Constraints**: Standard Alpha-Scope V3 intégral sur `services.py`/`router.py` (zones A/B/C, docstrings de règles métier, 25–30 lignes max, tri alphabétique strict) ; pas d'en-têtes `[RAG]` (phase 3) ; sessions DB via `get_db` exclusivement, `db` premier argument ; migrations via `make db-revision` uniquement

**Scale/Scope**: 5 domaines × 4 fichiers + ~10 fichiers de tests + seed ; 25 endpoints ; 6 migrations

## Constitution Check

*Gates dérivés de CLAUDE.md (constitution effective du projet — `.specify/memory/constitution.md` est un template vierge).*

| Gate | Source | Statut |
|---|---|---|
| Stack inflexible respectée (aucune substitution) | §4 | ✅ ajouts limités à bcrypt/httpx/extra email, dans la stack |
| 4 fichiers par domaine, structure §5 exacte | §5 | ✅ |
| Sessions DB via `get_db` uniquement, config via `settings` | §5 | ✅ |
| Domaines étanches — connaissance par FK explicites seulement | §5 | ✅ imports de modèles limités au sens des FK (D8) |
| Alpha-Scope V3 : zones A/B/C, `[FILE]`/`[CODE_START]`, tri alphabétique | §6 | ✅ gabarit jalon 4 |
| Aucun en-tête `[RAG]`/`[MODEL]`/`[SCHEMA]` écrit à la main | §6–7 | ✅ reportés phase 3 |
| Migrations via `make db-revision`, jamais `alembic revision` à la main | §4 bis | ✅ gate de chaque jalon |
| Validation par jalon avant le suivant | §8 | ✅ gate uniforme |
| Test permanent « un senior embaucherait-il ? » | §2 | ✅ cf. D5, D14 (pas d'unicité artificielle, bcrypt, PATCH partiel) |

**Post-design re-check** : aucun gate violé après Phase 1. Deux écarts
justifiés en Complexity Tracking (amendement ponctuel de la fondation,
imports inter-domaines).

## Project Structure

### Documentation (this feature)

```text
specs/001-phase2-domains/
├── plan.md              # Ce fichier
├── research.md          # Phase 0 — décisions D1–D14
├── data-model.md        # Phase 1 — tables, contraintes, schémas Pydantic
├── quickstart.md        # Phase 1 — guide de validation par jalon
├── contracts/
│   └── api.md           # Phase 1 — 25 endpoints, conventions d'erreurs
└── tasks.md             # Phase 2 (/speckit-tasks — pas encore créé)
```

### Source Code (repository root)

```text
app/
├── core/
│   └── database.py            # AMENDEMENT jalon 4 : naming_convention (D3)
├── domains/
│   ├── users/                 # Jalon 4 — GABARIT
│   │   ├── __init__.py
│   │   ├── models.py          # User, UserRole
│   │   ├── schemas.py         # UserBase/Create/Read/Update
│   │   ├── services.py        # create/delete/get/list/update_user
│   │   └── router.py          # 5 endpoints /api/v1/users
│   ├── organizations/         # Jalon 5 — déclinaison
│   ├── projects/              # Jalon 6 — déclinaison
│   ├── tasks/                 # Jalon 7 — déclinaison
│   └── comments/              # Jalon 8 — déclinaison
├── main.py                    # [STEP 2] : montage d'un routeur par jalon
└── scripts/
    └── seed.py                # Jalon 9

alembic/
├── env.py                     # un import de modèles décommenté/ajouté par jalon
└── versions/                  # une migration autogénérée par jalon (×6 max)

tests/
├── conftest.py                # fixtures partagées (D10) — créé au jalon 4
├── unit/
│   ├── test_users_schemas.py          # Jalon 4
│   ├── test_organizations_schemas.py  # Jalon 5
│   ├── test_projects_schemas.py       # Jalon 6
│   ├── test_tasks_schemas.py          # Jalon 7
│   ├── test_comments_schemas.py       # Jalon 8
│   └── test_seed.py                   # Jalon 9 (helpers purs du seed)
└── integration/
    ├── test_users_router.py           # Jalon 4
    ├── test_organizations_router.py   # Jalon 5
    ├── test_projects_router.py        # Jalon 6
    ├── test_tasks_router.py           # Jalon 7
    ├── test_comments_router.py        # Jalon 8
    └── test_seed_idempotence.py       # Jalon 9
```

**Structure Decision** : projet unique backend, structure §5 de CLAUDE.md
reprise à l'identique ; les tests suivent `tests/unit` + `tests/integration`
avec un fichier par domaine et par nature — nommage plat et prévisible
(`test_<domaine>_<objet>.py`), pas de sous-dossiers par domaine.

---

## Jalon 4 — users : LE GABARIT

Tout ce qui est défini ici vaut pour les jalons 5–8, qui n'en spécifient
que les différences.

### 4.0 — Préambule du jalon (une seule fois)

1. `app/core/database.py` : ajouter `NAMING_CONVENTION` et
   `metadata = MetaData(naming_convention=NAMING_CONVENTION)` sur `Base` (D3).
2. `pyproject.toml` : `bcrypt ^5.0`, `pydantic` → extras `["email"]`,
   `httpx ^0.28` (dev), `asyncio_default_fixture_loop_scope = "session"`.
3. `tests/conftest.py` : fixtures partagées (voir 4.5).

### 4.1 — Anatomie de `models.py`

En-tête `[FILE]` + docstring module, bloc `─── IMPORTS ───`,
`[CODE_START]`. Puis, dans cet ordre : enums du domaine (classe
`(str, Enum)`), classe modèle. Colonnes en style SQLAlchemy 2.0
(`Mapped[...]` / `mapped_column`), déclarées dans l'ordre : `id`, puis
colonnes métier par ordre alphabétique, puis `created_at`, `updated_at`.
`__table_args__` porte les contraintes nommées (CHECK, UNIQUE composées).
Pas de `relationship()` en phase 2 — les jointures passent par les FK
explicites, aucune navigation ORM inter-domaines.

### 4.2 — Anatomie de `schemas.py`

Marqueurs identiques. 4 classes en ordre alphabétique — `UserBase`,
`UserCreate`, `UserRead`, `UserUpdate` — selon le patron de
[data-model.md](data-model.md). `UserRead` porte
`model_config = ConfigDict(from_attributes=True)`. Aucune logique, aucune
méthode : les schémas sont des données pures.

### 4.3 — Anatomie de `services.py`

Fonctions triées alphabétiquement, toutes `async`, `db: AsyncSession`
**toujours premier argument**, arguments suivants triés alphabétiquement :

```python
async def create_user(db: AsyncSession, data: UserCreate) -> User
async def delete_user(db: AsyncSession, user_id: int) -> None
async def get_user(db: AsyncSession, user_id: int) -> User
async def list_users(db: AsyncSession, limit: int, offset: int) -> Sequence[User]
async def update_user(db: AsyncSession, data: UserUpdate, user_id: int) -> User
```

Chaque fonction : **Zone A** — docstring de règles métier, invariants et
cas limites (jamais une paraphrase du nom) ; **Zone B** — bloc
`─── ZONE DE DÉCLARATION DES VARIABLES ───`, toutes les variables locales
typées et triées, avant toute logique ; **Zone C** — étapes `[STEP n]`
avec postcondition `→`, 25–30 lignes maximum.

Règles métier portées par les services (pas par les routeurs) :

- `create_user` / `update_user` : unicité email (SELECT préalable → 409),
  hachage bcrypt du mot de passe via helpers privés du module
  (`_hash_password(password: str) -> str`, seul code non-CRUD du fichier,
  trié avec les autres fonctions — le préfixe `_` le place en tête).
- `get_user` / `update_user` / `delete_user` : 404 si id inconnu.
- `delete_user` : 409 si propriétaire d'organisations ou auteur de
  commentaires (D2) — **note** : ces deux vérifications n'arrivent
  qu'aux jalons 5 et 8 respectivement, chacune ajoutée quand la table
  référençante existe. La fonction est créée au jalon 4 avec un DELETE
  simple, puis complétée — c'est la seule retouche inter-jalons autorisée.
- Les services font `await db.commit()` puis `await db.refresh(...)` ;
  une écriture par requête HTTP.

### 4.4 — Anatomie de `router.py`

`router = APIRouter(prefix="/users", tags=["users"])`. Cinq handlers,
mêmes noms que les fonctions de service (wrapper mince), tri alphabétique,
`db: AsyncSession = Depends(get_db)`. Statuts : 201/204/200 selon
[contracts/api.md](contracts/api.md). Pagination :
`limit: int = Query(default=50, ge=1, le=100)`,
`offset: int = Query(default=0, ge=0)`. Les handlers ne contiennent
**aucune** logique : appel du service, retour du modèle (sérialisé par
`response_model=UserRead`). Montage dans `app/main.py` [STEP 2] :
`app.include_router(users_router, prefix="/api/v1")`.

### 4.5 — Patron des tests

`tests/conftest.py` (D10) :

- `db_engine` (scope session) : dérive le DSN de test en remplaçant le nom
  de base par `alpha_scope_test` ; crée la base si absente (connexion
  AUTOCOMMIT sur la base `postgres`) ; `drop_all` + `create_all` de
  `Base.metadata` ; dispose en fin de session.
- `db_session` (scope function) : session liée au moteur de test.
- `client` (scope function) : `httpx.AsyncClient` + `ASGITransport` sur
  `create_app()` avec `dependency_overrides[get_db]` → session de test ;
  lifespan non exécuté (le moteur de test remplace celui du lifespan).
- Autouse (scope function) : `TRUNCATE <toutes les tables> RESTART
  IDENTITY CASCADE` après chaque test.

`tests/unit/test_users_schemas.py` — sans DB : payload valide accepté,
email invalide rejeté, rôle hors enum rejeté, mot de passe < 8 rejeté,
`UserUpdate()` vide valide, longueurs max respectées.

`tests/integration/test_users_router.py` — parcours API complet, une
fonction de test par scénario d'acceptation + cas limites du contrat :
create 201 (sans champ mot de passe dans la réponse), doublon email 409,
get 200/404, list + pagination (défauts, bornes, 422), patch partiel 200 /
404 / email dupliqué 409, delete 204 puis get 404, delete id inconnu 404.

### 4.6 — Migration et gate

`alembic/env.py` : décommenter/ajouter
`from app.domains.users import models as users_models  # noqa: F401`.
Puis le **gate uniforme** ([quickstart.md](quickstart.md)) :

```bash
make db-revision m="users_domain" && make db-migrate
poetry run pytest
poetry run mypy app alembic tests
poetry run ruff check app alembic tests && poetry run ruff format --check app alembic tests
```

---

## Jalons 5–8 — Déclinaisons du gabarit

Chaque jalon = 4 fichiers + 2 fichiers de tests + import dans
`alembic/env.py` + montage du routeur dans `main.py` + gate uniforme
(`m="<domaine>_domain"`). Seules les différences sont listées ;
champs et contraintes exacts dans [data-model.md](data-model.md),
endpoints dans [contracts/api.md](contracts/api.md).

### Jalon 5 — organizations

- **FK** : `owner_id → users.id`, `ondelete=RESTRICT`.
- **Services** : `create_organization` vérifie l'existence de l'owner
  (SELECT sur `User` → 404, D7/D8) et l'unicité du nom (409) ;
  `delete_organization` : DELETE simple (la vérification « contient des
  projets » arrive au jalon 6).
- **Retouche users** : `delete_user` gagne sa vérification 409
  « possède des organisations ».
- **Update** : `OrganizationUpdate` = `{name?}` — owner non modifiable.
- **Tests d'intégration en plus du patron** : owner inexistant → 404 ;
  suppression de l'owner → 409.

### Jalon 6 — projects

- **FK** : `organization_id → organizations.id`, `ondelete=RESTRICT` ;
  UNIQUE `(organization_id, name)`.
- **Services** : `create_project` vérifie l'organisation (404) et
  l'unicité du nom dans l'org (409) ; `delete_project` : DELETE simple —
  la cascade vers les tâches est du ressort de la DB (jalon 7).
- **Retouche organizations** : `delete_organization` gagne sa
  vérification 409 « contient des projets ».
- **Update** : `{name?, description?}` — organisation non modifiable.
- **Tests en plus** : org inexistante → 404 ; doublon de nom dans la même
  org → 409, même nom dans une autre org → 201 ; suppression de l'org
  occupée → 409.

### Jalon 7 — tasks

- **FK** : `project_id → projects.id` `ondelete=CASCADE` ;
  `assignee_id → users.id` `ondelete=SET NULL`, **nullable**.
- **Enums** : `TaskStatus`, `TaskPriority` (D1) — deux CHECK nommés.
- **Services** : `create_task` vérifie le projet (404) et, si fourni,
  l'assigné (404) ; `update_task` vérifie l'assigné si présent dans le
  payload ; sémantique `exclude_unset` pour la désassignation
  (`"assignee_id": null`).
- **Update** : `{title?, description?, status?, priority?, assignee_id?}`
  — projet non modifiable.
- **Tests en plus** : enum invalide → 422 ; assignation/désassignation via
  PATCH ; suppression du projet → tâches disparues (cascade DB) ;
  suppression de l'assigné → tâche conservée, `assignee_id` NULL.

### Jalon 8 — comments

- **FK** : `task_id → tasks.id` `ondelete=CASCADE` ;
  `author_id → users.id` `ondelete=RESTRICT`.
- **Services** : `create_comment` vérifie tâche et auteur (404) ;
  `list_comments(db, limit, offset, task_id)` exige `task_id` et vérifie
  son existence (404).
- **Retouche users** : `delete_user` gagne sa vérification 409
  « a des commentaires » — la fonction atteint sa forme finale.
- **Update** : `{content?}` — tâche et auteur non modifiables.
- **Tests en plus** : liste filtrée par tâche (et uniquement elle) ;
  `GET /comments` sans `task_id` → 422 ; suppression de la tâche →
  commentaires disparus ; suppression d'un auteur → 409 ; chaîne complète
  de cascade projet → tâches → commentaires.

---

## Jalon 9 — Seed idempotent

- `app/scripts/seed.py` (Alpha-Scope V3 intégral) : jeu de données
  constant au niveau module ; get-or-create par clé naturelle (D11) dans
  l'ordre users → organizations → projects → tasks → comments ; moteur via
  `init_db_engine()` + `async_session_factory` (jamais de session à la
  main) ; exécutable `python -m app.scripts.seed`.
- Couverture obligatoire du jeu : les 6 arêtes FK, 2 rôles, 3 statuts,
  3 priorités, tâches assignées et non assignées, ≥2 commentaires sur une
  même tâche. Volumes indicatifs : 5 users, 2 orgs, 4 projects, 12 tasks,
  8 comments.
- `Makefile` : `db-seed` remplace son écho par
  `poetry run python -m app.scripts.seed`.
- **Tests** : `test_seed_idempotence.py` — exécuter le seed deux fois dans
  la base de test, comparer les comptes de lignes et l'ensemble des clés
  naturelles (identiques) ; vérifier la couverture (arêtes, enums).
  `test_seed.py` (unit) — helpers purs éventuels du module.
- **Gate** : identique, sans `make db-revision` (aucun changement de
  schéma) — sauf si autogenerate détecte une dérive, qui serait alors un
  bug à corriger avant clôture.

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Amendement de `app/core/database.py` (fondation Phase 1 validée) pour la `naming_convention` | Les CHECK de D1 et l'autogenerate exigent des contraintes nommées déterministes | Nommer chaque contrainte à la main dans chaque modèle : répétitif, incohérences garanties à 5 domaines |
| `services.py` importe les `models.py` d'autres domaines (sens des FK uniquement, D8) | FR-002 : vérifier l'existence des références et nommer l'entité fautive dans l'erreur | Traduire les `IntegrityError` du driver : messages non maîtrisés, parsing fragile, non déterministe |
| `delete_user` / `delete_organization` retouchés aux jalons 5, 6 et 8 | Une vérification 409 ne peut exister avant la table qu'elle interroge ; l'ordre strict des jalons l'impose | Créer les vérifications dès le jalon 4 : référencerait des modèles inexistants ; tout livrer en un jalon : violerait le plan §8 |
