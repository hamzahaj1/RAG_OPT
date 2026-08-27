# Research — Phase 2 : Domaines métier

**Feature**: `001-phase2-domains` | **Date**: 2026-08-27

Toutes les inconnues du Technical Context sont résolues ici. D1 et D2 sont
**imposées** par l'utilisateur ; les autres sont des décisions dérivées,
prises pour maximiser le déterminisme (CLAUDE.md §10).

---

## D1 — Enums : Python `(str, Enum)` + `String` + CHECK *(imposée)*

**Decision** : chaque ensemble fermé (rôle, statut, priorité) est un enum
Python `class X(str, Enum)` dans `models.py`, persisté en colonne
`String` avec une `CheckConstraint` **nommée** côté PostgreSQL.

**Rationale** : l'ENUM natif PostgreSQL exige des `ALTER TYPE` que
l'autogenerate Alembic gère mal — chaque évolution de valeurs produirait
des migrations manuelles imprévisibles. String + CHECK donne des
migrations 100 % autogénérées et déterministes.

**Alternatives considered** : ENUM natif PostgreSQL (rejeté : ALTER
pénible) ; `sqlalchemy.Enum(native_enum=False)` (rejeté : génère un
VARCHAR + CHECK mais avec un nommage et une longueur implicites — moins
lisible dans la migration que la contrainte explicite).

## D2 — Politique de suppression : double couche *(imposée)*

**Decision** : chaque règle de suppression est implémentée **deux fois** —
au niveau service (vérification explicite + `HTTPException` 409) et au
niveau DB (`ondelete` sur la FK). La DB garantit, le service explique.

| Arête FK | `ondelete` | Comportement service |
|---|---|---|
| `organizations.owner_id → users.id` | `RESTRICT` | `delete_user` : 409 si l'utilisateur possède ≥1 organisation |
| `comments.author_id → users.id` | `RESTRICT` | `delete_user` : 409 si l'utilisateur a ≥1 commentaire |
| `tasks.assignee_id → users.id` | `SET NULL` | `delete_user` : aucune vérification — la DB désassigne |
| `projects.organization_id → organizations.id` | `RESTRICT` | `delete_organization` : 409 si ≥1 projet |
| `tasks.project_id → projects.id` | `CASCADE` | `delete_project` : suppression directe, la DB cascade |
| `comments.task_id → tasks.id` | `CASCADE` | `delete_task` : suppression directe, la DB cascade |

**Rationale** : le blocage des auteurs de commentaires est confirmé comme
choix conscient — règle la plus déterministe (jamais de contenu orphelin ni
de suppression silencieuse de contenu).

## D3 — Convention de nommage des contraintes sur `Base.metadata`

**Decision** : ajouter une `naming_convention` à la métadonnée de `Base`
dans `app/core/database.py` (amendement ponctuel de la fondation, ouvert
au jalon 4) :

```python
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
```

**Rationale** : sans convention, PostgreSQL nomme les contraintes lui-même
et Alembic autogenerate produit des migrations non déterministes (drops
impossibles à nommer). Prérequis direct de D1 (CHECK nommés).

**Alternatives considered** : nommer chaque contrainte à la main dans
chaque modèle (rejeté : répétitif, source d'incohérences — exactement ce
que la convention élimine).

## D4 — Clés primaires et horodatages

**Decision** : PK `int` autoincrémentée (`Mapped[int]`,
`primary_key=True`) sur les cinq tables. Colonnes `created_at` /
`updated_at` : `DateTime(timezone=True)`, `server_default=func.now()`,
`onupdate=func.now()` pour `updated_at`.

**Rationale** : entiers séquentiels = seed et fixtures déterministes,
lisibles dans les chunks RAG. UUID n'apporte rien ici (pas de
distribution, pas d'exposition publique).

**Alternatives considered** : UUID v4 (rejeté : non déterministe, bruit
dans le corpus) ; trigger PostgreSQL pour `updated_at` (rejeté : logique
hors du code, invisible pour le parsing AST).

## D5 — Hachage des mots de passe : `bcrypt` direct

**Decision** : dépendance `bcrypt` (^5.0), appelée directement dans
`services.py` du domaine users via deux petites fonctions privées du
module. Le hash n'apparaît dans aucun schéma de réponse.

**Rationale** : FR-009 exige un stockage irréversible. `bcrypt` est le
standard minimal crédible ; `passlib` n'est plus maintenu.

**Alternatives considered** : `passlib[bcrypt]` (rejeté : projet à
l'abandon, warnings avec bcrypt ≥4) ; `pbkdf2_hmac` stdlib (rejeté : un
senior utiliserait bcrypt/argon2) ; `argon2-cffi` (viable, mais bcrypt
suffit et a des type hints intégrés).

## D6 — Validation email : `EmailStr` + extra `pydantic[email]`

**Decision** : `pydantic = { extras = ["email"], version = "^2.11.0" }` ;
le champ `email` des schémas users est un `EmailStr`.

**Rationale** : validation d'email déclarative, visible dans le schéma —
aucune logique de validation manuelle.

## D7 — Vérification des FK à l'écriture : SELECT explicite + backstop DB

**Decision** : à la création/modification, le service vérifie l'existence
de chaque entité référencée par un SELECT explicite et lève
`HTTPException(404, "User 42 not found")` (l'entité fautive est nommée).
La contrainte FK PostgreSQL reste le filet de sécurité.

**Rationale** : FR-002 exige une erreur explicite désignant la référence
fautive. Traduire les `IntegrityError` en messages demanderait de parser
les libellés du driver — fragile et non déterministe. Même philosophie
« double couche » que D2.

**Alternatives considered** : catch `IntegrityError` seul (rejeté :
message non maîtrisé, mapping fragile).

## D8 — Étanchéité des domaines : imports uniquement le long des FK

**Decision** : un `services.py` peut importer **uniquement** les
`models.py` des domaines que ses FK référencent, dans le sens de la FK :
`organizations → users` ; `projects → organizations` ;
`tasks → projects, users` ; `comments → tasks, users`. Jamais de schéma ni
de service d'un autre domaine, jamais d'import remontant.

**Rationale** : « un domaine ne connaît les autres que par leurs FK
explicites » (CLAUDE.md §5) — l'import du modèle référencé matérialise
exactement cette connaissance, sans cycle possible (le graphe FK est
acyclique).

## D9 — Conventions API

**Decision** :

- Préfixe commun `/api/v1`, monté dans `create_app` ; chaque routeur
  déclare `APIRouter(prefix="/users", tags=["users"])` etc.
- Verbes/statuts : `POST` → 201, `GET` (item et liste) → 200,
  `PATCH` (partiel) → 200, `DELETE` → 204. 404 = introuvable (path **ou**
  référence FK), 409 = conflit (unicité, suppression bloquée),
  422 = validation Pydantic.
- Pagination uniforme : `offset` (≥0, défaut 0), `limit` (1–100, défaut
  50) via `Query`, réponse = liste plate.
- `GET /api/v1/comments` exige `task_id` (FR-021) ; 404 si la tâche
  n'existe pas.

**Rationale** : cinq domaines, une seule grammaire — condition de la
régularité géométrique.

## D10 — Infrastructure de test

**Decision** :

- Base dédiée `alpha_scope_test` sur le même PostgreSQL 16 conteneurisé ;
  DSN dérivé de `settings.database_url` en remplaçant le nom de base
  (aucune nouvelle variable d'environnement).
- `tests/conftest.py` : fixture session (`loop_scope="session"`) qui crée
  la base si absente (connexion AUTOCOMMIT sur la base `postgres`), puis
  `drop_all`/`create_all` de `Base.metadata` une fois par session ;
  fixture fonction autouse qui `TRUNCATE ... RESTART IDENTITY CASCADE`
  toutes les tables après chaque test.
- Client HTTP : `httpx.AsyncClient` + `ASGITransport` sur `create_app()`,
  avec `app.dependency_overrides[get_db]` → sessions de la factory de
  test. Ajouter `asyncio_default_fixture_loop_scope = "session"` à
  `[tool.pytest.ini_options]`.
- Partage unit/integration : `tests/unit/` = schémas, enums, helpers purs
  (sans DB) ; `tests/integration/` = parcours API complets contre
  PostgreSQL réel (jamais SQLite — imposé).

**Rationale** : les CHECK, FK `ondelete` et types PostgreSQL font partie
du comportement testé (D1, D2) — un substitut en mémoire ne les exécuterait
pas. `create_all` (et non `alembic upgrade`) dans les tests : rapide, et
les migrations sont validées séparément par le gate `make db-migrate` de
chaque jalon.

**Alternatives considered** : transaction-rollback par test (rejeté :
interactions subtiles avec les commits des services — TRUNCATE est plus
prévisible) ; testcontainers (rejeté : le conteneur compose existe déjà).

## D11 — Seed idempotent : get-or-create par clé naturelle

**Decision** : `app/scripts/seed.py` définit un jeu de données constant au
niveau module et applique un get-or-create (SELECT par clé naturelle,
INSERT si absent, sinon aucune écriture) dans l'ordre des dépendances :
users → organizations → projects → tasks → comments. Clés naturelles :

| Entité | Clé naturelle | Adossée à une contrainte UNIQUE |
|---|---|---|
| User | `email` | oui |
| Organization | `name` | oui |
| Project | `(organization_id, name)` | oui |
| Task | `(project_id, title)` | non (SELECT-first suffit, seed mono-connexion) |
| Comment | `(task_id, author_id, content)` | non (idem) |

Le jeu couvre les six arêtes FK, les trois statuts, les trois priorités,
les deux rôles, des tâches assignées et non assignées. Exécution :
`poetry run python -m app.scripts.seed` derrière `make db-seed`.

**Rationale** : SC-004 (relance N fois → état strictement identique) sans
`ON CONFLICT` spécifique PostgreSQL dans le code applicatif.

**Alternatives considered** : `INSERT ... ON CONFLICT DO NOTHING`
(rejeté : illisible pour les clés composées sans contrainte) ; TRUNCATE
puis ré-insertion (rejeté : destructif, pas idempotent au sens de la spec).

## D12 — Colonnes communes répétées, pas de mixin

**Decision** : `id`, `created_at`, `updated_at` sont déclarées
explicitement dans chacun des cinq `models.py` — aucun mixin partagé.

**Rationale** : régularité plutôt qu'élégance ponctuelle (CLAUDE.md §10).
Chaque `models.py` est autosuffisant pour le chunking : un chunk de modèle
contient 100 % de ses colonnes sans résolution d'héritage.

## D13 — Dépendances ajoutées

**Decision** :

- Principales : `bcrypt ^5.0` (D5) ; `pydantic` passe à
  `{ extras = ["email"] }` (D6).
- Dev : `httpx ^0.28` (client de test ASGI, D10).

Aucune autre dépendance. `greenlet` arrive transitivement via SQLAlchemy.

## D14 — Contraintes d'unicité

**Decision** : `users.email` UNIQUE ; `organizations.name` UNIQUE ;
`projects` UNIQUE `(organization_id, name)` (contrainte nommée
`uq_projects_organization_id`... générée par D3). Pas d'unicité sur
`tasks.title` ni `comments` — irréaliste pour un clone Jira/Linear.

**Rationale** : FR-007 (email) ; D11 (clés naturelles du seed) ; le test
permanent « un senior embaucherait-il ? » interdit d'imposer des titres de
tâches uniques.
