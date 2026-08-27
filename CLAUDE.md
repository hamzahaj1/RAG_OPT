# Alpha-Scope RAG — Charte de projet

> Document de référence unique. Lisible par un humain et par une IA.
> À placer à la racine du projet sous le nom `CLAUDE.md`.

---

## 1. But

Construire un **pipeline RAG capable d'analyser du code source avec un taux
d'erreur de génération proche de 0 %**.

Ce but se décompose en deux objets distincts qui doivent être construits dans
l'ordre :

**La cible** — une application web FastAPI dont la structure géométrique et
syntaxique est si régulière qu'une IA peut la découper, l'indexer et la raisonner
sans ambiguïté. La régularité n'est pas cosmétique : c'est le livrable réel.

**Le tireur** — un pipeline GraphRAG couplé à un LLM de raisonnement profond
qui ingère cette cible via parsing AST et indexation vectorielle, avec une boucle
d'auto-correction agentique en sandbox.

On construit d'abord la cible parfaite, ensuite le tireur.

---

## 2. Contrainte non négociable

Le code doit être **simultanément** :

- **Réel et moderne** — stack crédible, patterns qu'un développeur senior
  reconnaît immédiatement, structure qu'une équipe de production utiliserait.
- **Géométriquement parfait** — régulier et prévisible au point d'être ingérable
  sans bruit par un pipeline RAG.

Ce n'est pas contradictoire : les meilleures bases de code sont déjà régulières.
Le standard Alpha-Scope pousse cette régularité à son maximum formel.

Test permanent à chaque décision : *est-ce qu'un senior FastAPI embaucherait
quelqu'un qui a écrit ça ?*

---

## 3. Domaine fonctionnel

Plateforme de gestion de projets (style Jira/Linear simplifié).

| Domaine | Rôle |
|---|---|
| `users` | authentification, rôles |
| `organizations` | ownership des projets |
| `projects` | domaine central |
| `tasks` | statuts, priorités, assignation |
| `comments` | relations imbriquées sur les tâches |

**Relations FK cross-domaines :**

```
organizations.owner_id   → users.id
projects.organization_id → organizations.id
tasks.project_id         → projects.id
tasks.assignee_id        → users.id
comments.task_id         → tasks.id
comments.author_id       → users.id
```

---

## 4. Stack technique

Inflexible. Aucune substitution sans décision explicite.

**Backend**
- Python 3.11+, typage statique strict et obligatoire
- FastAPI (asynchrone)
- SQLAlchemy 2.0 — sessions asynchrones avec `asyncpg`
- PostgreSQL 16
- Alembic — migrations
- Pydantic V2 — schémas stricts
- Poetry — dépendances
- Ruff — linter et formatter
- MyPy — typage strict
- Pytest — tests

**Frontend**
- React 18+ avec TypeScript
- Vite
- TailwindCSS
- TanStack Query — data fetching et cache
- Zustand — état global
- React Hook Form + Zod — formulaires

**Infrastructure**
- Docker Compose — PostgreSQL, backend, frontend, Adminer

**Étape 2**
- GraphRAG — indexation vectorielle
- DeepSeek-R1 — LLM de raisonnement

---

## 4 bis. Décisions d'environnement

Décisions locales actées, à ne pas remettre en cause sans nouvelle décision explicite.

- **Runtime conteneurs** : Podman + podman-compose (le Makefile appelle `podman compose`).
  `docker-compose.yml` reste 100 % standard ; images qualifiées `docker.io/library/...`.
- **Python local** : 3.14 (contrainte projet `>=3.11`), `asyncpg ^0.31` requis.
- **Poetry 2.4.1** installé via `pip --user`.
- **Alembic** : `alembic.ini` à la racine, `sqlalchemy.url` neutralisée — `env.py`
  lit exclusivement `settings.database_url`. Migration initiale vide
  `f2476b2dee09_initial_schema` conservée comme baseline du pipeline.
- **Génération de migrations** : toujours via `make db-revision m="message"`
  (autogenerate + `ruff check --fix` + `ruff format` sur `alembic/versions/`),
  jamais `alembic revision` à la main.

---

## 5. Architecture

Clean Architecture fusionnée avec Domain-Driven Design.
Domaines étanches, sans dépendances croisées non maîtrisées.

```
alpha_scope_rag/
├── CLAUDE.md                      # Ce document
├── CONTRACTS.md                   # Contrats inter-domaines
├── TOPOLOGY.yaml                  # Graphe d'appels (généré)
├── pyproject.toml
├── docker-compose.yml
├── Makefile
├── alembic/
├── app/
│   ├── main.py                    # Assemblage FastAPI, routeurs, cycle de vie DB
│   ├── core/
│   │   ├── config.py              # Settings pydantic-settings, DSN PostgreSQL
│   │   └── database.py            # Moteur async, AsyncSessionFactory, get_db()
│   ├── domains/
│   │   ├── users/
│   │   ├── organizations/
│   │   ├── projects/
│   │   ├── tasks/
│   │   └── comments/
│   │       ├── models.py          # SQLAlchemy       — annoté [MODEL]
│   │       ├── schemas.py         # Pydantic V2      — annoté [SCHEMA]
│   │       ├── services.py        # Logique métier   — annoté [RAG]
│   │       └── router.py          # Endpoints        — annoté [RAG]
│   └── scripts/
│       └── seed.py
├── scripts/
│   ├── generate_topology_headers.py
│   └── generate_structural_metadata.py
├── frontend/
└── tests/
    ├── unit/
    └── integration/
```

**Règles d'architecture :**
- Sessions DB obtenues exclusivement via la dépendance `get_db`
- Configuration lue exclusivement via le singleton `settings`
- Un domaine ne connaît les autres que par leurs FK explicites
- Code 100 % typé, sans raccourcis

---

## 6. Standard Alpha-Scope V3

S'applique à **toutes** les fonctions de **tous** les fichiers.
Aucune exception, aucun raccourci.

Chaque fonction porte un en-tête RAG compressé, puis est découpée en trois zones
internes étanches.

### Zone 0 — En-tête `[RAG]`

Bloc de métadonnées machine-readable placé avant la signature.

| Champ | Contenu |
|---|---|
| `signature` | nom + types d'entrée et de sortie |
| `weight` | poids calculé à partir des appels entrants et sortants |
| `tier` | `CRITICAL_CORE` \| `CORE` \| `LEAF` |
| `calls` | fonctions appelées par celle-ci |
| `called_by` | fonctions qui appellent celle-ci |
| `reads` | tables et entités lues |
| `mutates` | tables et entités mutées |

### Zone A — Contrat

Arguments triés, `db` toujours en premier position, docstring.

La docstring documente les **règles métier, invariants et cas limites** —
jamais une reformulation du nom de la fonction.

### Zone B — Empreinte

Toutes les variables locales déclarées et triées, typage explicite sur chaque
ligne, avant toute logique ou structure de contrôle.

```python
# ─── ZONE DE DÉCLARATION DES VARIABLES ───
project: Optional[Project] = None
update_data: dict
# ─────────────────────────────────────────
```

### Zone C — Algorithme

Étapes balisées `[STEP]`, maximum 25 à 30 lignes.
La borne porte sur la Zone C (algorithme), mesurée du premier `[STEP]` à la
dernière ligne. Les zones A et B ne sont pas bornées.

Chaque `[STEP]` porte une **postcondition** notée `→` : ce qui est *résolu* après
l'étape, pas une paraphrase de la ligne de code.

```python
# [STEP 1] Charger le projet cible  → project est chargé ou None
# [STEP 2] Vérifier l'ownership     → l'appelant est autorisé à muter
```

### Règle transversale — Ordre alphabétique déterministe

Dans un même fichier, les fonctions sont triées par ordre alphabétique strict de
leur nom. Aucun regroupement par « logique métier ».

Le tri est **ASCII strict** : l'underscore (`0x5F`) précède les minuscules, donc
les helpers privés préfixés `_` apparaissent avant l'API publique du fichier
(ex. `_hash_password` avant `create_user`).

```python
async def create_project(...)
async def delete_project(...)
async def get_project(...)
async def list_projects(...)
async def update_project(...)
```

### Marqueurs de chunking

- `[FILE]` en tête de fichier
- `[CODE_START]` après le bloc d'imports

Ces marqueurs permettent au pipeline d'ignorer le boilerplate d'imports lors du
découpage.

---

## 7. Génération automatique des métadonnées

Les annotations ne sont **jamais** écrites à la main. Deux scripts les produisent
par analyse AST.

**`generate_topology_headers.py`**
Analyse l'AST, résout les imports et alias de module, calcule `weight` et `tier`,
insère les en-têtes `[RAG]` dans `services.py` et `router.py`.

**`generate_structural_metadata.py`**
Insère `[MODEL]` sur `models.py`, `[SCHEMA]` sur `schemas.py`, produit
`TOPOLOGY.yaml`.

> Piège connu : dans un heredoc bash, le pattern regex `["\']` se corrompt.
> Utiliser `(?:'|")`.

---

## 8. Plan d'exécution

Un jalon = un prompt = un livrable vérifiable.
Chaque jalon doit être validé avant de passer au suivant.

### Phase 1 — Fondation

| # | Jalon | Livrable | Validation |
|---|---|---|---|
| 0 | Charte | `CLAUDE.md` à la racine | Fichier lu par Claude Code |
| 1 | Environnement | `pyproject.toml`, `docker-compose.yml`, `Makefile`, `.env.example` | `make up` démarre PostgreSQL |
| 2 | Noyau | `app/core/config.py`, `app/core/database.py`, `app/main.py` | L'app démarre, `/docs` répond |
| 3 | Migrations | Alembic configuré en async | `make db-migrate` passe |

> ✅ **Phase 1 validée le 2026-08-27** (jalons 0–3) : `make up` opérationnel,
> `/docs` et `/health` répondent, `make db-migrate` passe, MyPy strict et
> Ruff verts sur `app/` et `alembic/`.

### Phase 2 — Domaines

| # | Jalon | Livrable | Validation |
|---|---|---|---|
| 4 | `users` | 4 fichiers + tests | CRUD complet, tests verts |
| 5 | `organizations` | 4 fichiers + tests | FK vers users fonctionnelle |
| 6 | `projects` | 4 fichiers + tests | FK vers organizations fonctionnelle |
| 7 | `tasks` | 4 fichiers + tests | FK vers projects et users |
| 8 | `comments` | 4 fichiers + tests | FK vers tasks et users |
| 9 | Seed | `app/scripts/seed.py` idempotent | `make db-seed` peuple la DB |

> ✅ **Jalon 4 (`users`) validé le 2026-08-27** — gate complet vert : contrôle de
> dérive (`make db-revision` → migration vide), `make db-migrate`, 20 tests
> pytest (12 integration + 8 unit), MyPy `--strict` sur 22 fichiers, Ruff
> `check` + `format --check`. Le domaine `users` est le **gabarit de référence
> pour les jalons 5–8**.
>
> **Écarts assumés du jalon 4** (actés, à ne pas « corriger » sans décision) :
> - **Makefile `db-revision`** : exécute `ruff format` **puis** `ruff check --fix`
>   (ordre inverse de §4 bis) — résultat final identique, les deux outils verts.
> - **Boucle asyncio de session** : `asyncio_default_fixture_loop_scope` et
>   `asyncio_default_test_loop_scope = "session"` dans `pyproject.toml` — un seul
>   event loop partagé par toute la suite, requis par le moteur async unique des
>   tests d'intégration.
> - **B008 / `Depends`** : neutralisé finement via
>   `[tool.ruff.lint.flake8-bugbear] extend-immutable-calls =
>   ["fastapi.Depends", "fastapi.Query"]` — pattern FastAPI canonique, pas
>   d'ignore global de la règle.
> - **Fixture TRUNCATE** (`RESTART IDENTITY CASCADE` sur
>   `Base.metadata.sorted_tables`) confinée à `tests/integration/conftest.py` :
>   les tests unitaires restent exécutables sans PostgreSQL (D10).
> - **`__init__.py` dans `tests/`, `tests/unit/`, `tests/integration/`** :
>   paquets explicites pour la résolution des modules de test sous MyPy
>   `--strict` et pytest.
>
> **Engagement jalon 5** : ajouter le 409 « User still owns organizations » sur
> `delete_user` dès que la table `organizations` existe (retouche T017,
> re-exécution des tests T018).

> ✅ **Jalon 5 (`organizations`) validé le 2026-08-27** — gate T022 complet
> vert : `make db-revision m="organizations_domain"` → migration
> `1d70e9de6246` portant la **première FK du projet,
> `fk_organizations_owner_id_users`**, strictement conforme au patron `fk` de
> la `NAMING_CONVENTION` de T001 (avec `pk_organizations`,
> `uq_organizations_name`, `ix_organizations_owner_id`, `ondelete=RESTRICT`) ;
> `make db-migrate` ; 40 tests pytest (27 integration + 13 unit) ; MyPy
> `--strict` sur 30 fichiers ; Ruff `check` + `format --check` verts.
>
> **Engagement jalon 5 honoré** : retouche T017 exécutée comme consignée —
> `[STEP]` 409 « User {id} still owns organizations » ajouté à `delete_user`
> de façon additive (zones A/C mises à jour, pas de réorganisation), suivie de
> T018 : re-exécution des tests users, zéro régression. Avant photocopie, le
> gabarit avait aussi gagné le test d'intégration PATCH-role en round-trip
> API → DB → API (chemin sans `mode="json"`), portant les tests users à 21.
>
> **Engagement jalon 6** : ajouter le 409 « Organization {id} still has
> projects » sur `delete_organization` dès que la table `projects` existe
> (retouche T027, re-exécution des tests T028).

> ✅ **Jalon 6 (`projects`) validé le 2026-08-27** — gate T032 complet vert :
> `make db-revision m="projects_domain"` → migration `677e300dd994`
> (`fk_projects_organization_id_organizations`, `ix_projects_organization_id`,
> `ondelete=RESTRICT`, unicité composée `(organization_id, name)`) ;
> `make db-migrate` ; 61 tests pytest (43 integration + 18 unit) ; MyPy
> `--strict` ; Ruff verts. **Engagement jalon 6 honoré** : retouche T027
> additive sur `delete_organization` (`[STEP]` 409 « Organization {id} still
> has projects », zones A/C mises à jour), puis T028 : re-exécution des tests
> des jalons 4–5, zéro régression. La **chaîne bloquante
> users → organizations → projects est complète** : chaque suppression amont
> est refusée en 409 tant qu'une ligne aval la référence (double couche D2) ;
> la cascade ne descendra que de projects vers tasks/comments (Jalons 7–8).
>
> **Correctif au patron `uq` de la `NAMING_CONVENTION`** (acté au jalon 6) :
> `"uq": "uq_%(table_name)s_%(column_0_N_name)s"` — toutes les colonnes d'une
> contrainte composée entrent dans le nom, pas seulement la première. Raison :
> nom sémantiquement fidèle pour les contraintes composées, signal RAG (le nom
> seul décrit la portée exacte de l'unicité). Mono-colonne inchangé
> (`uq_organizations_name`) ; migration de renommage `a48ad14da82b` →
> `uq_projects_organization_id_name`, re-gate vert (61 tests, MyPy, Ruff).

> ✅ **Jalon 7 (`tasks`) validé le 2026-08-27** — gate T040 complet vert :
> `make db-revision m="tasks_domain"` → migration `443e75f588d9` portant les
> **premiers `ondelete=CASCADE` et `ondelete=SET NULL` du projet** :
> `fk_tasks_project_id_projects` (CASCADE, NOT NULL, `ix_tasks_project_id`)
> et `fk_tasks_assignee_id_users` (SET NULL, nullable,
> `ix_tasks_assignee_id`), plus les deux CHECK nommés d'ensembles fermés
> `ck_tasks_status` {todo, in_progress, done} et `ck_tasks_priority`
> {low, medium, high} ; `make db-migrate` ; 88 tests pytest (60 integration +
> 28 unit) ; MyPy `--strict` sur 47 fichiers ; Ruff `check` +
> `format --check` verts.
>
> Les **deux axes de suppression sont verrouillés par tests bidirectionnels**
> d'intégration : axe de contenance — suppression du projet → ses tâches
> disparaissent (cascade DB), et sens inverse — la tâche vivante retient son
> `project_id` ; axe de référence — suppression de l'assigné → 204, la tâche
> **subsiste** avec `assignee_id: null` (SET NULL, DB seule, sans double
> couche D2 : première dérogation assumée au patron 409, actée au plan), et
> sens inverse — désassignation applicative via PATCH `"assignee_id": null`
> (sémantique `exclude_unset` : champ absent ≠ null explicite).
> **Aucune retouche inter-jalons au jalon 7** (aucun engagement hérité :
> `delete_user` vs assignation = SET NULL porté par la DB seule).
>
> **Engagement jalon 8** : ajouter le 409 « User {id} still has comments » sur
> `delete_user` dès que la table `comments` existe (retouche T045 — **forme
> finale** de la fonction, docstring énonçant les deux blocages —, puis T046 :
> re-exécution des tests des jalons 4–7).

> ✅ **Jalon 8 (`comments`) validé le 2026-08-27** — gate T050 complet vert :
> `make db-revision m="comments_domain"` → migration `3b55d9e3f2bf`
> (`fk_comments_task_id_tasks`, `ondelete=CASCADE` ;
> `fk_comments_author_id_users`, `ondelete=RESTRICT` ; `ix_comments_task_id`,
> `ix_comments_author_id`) ; `make db-migrate` ; 111 tests pytest
> (77 integration + 34 unit) ; MyPy `--strict` sur 55 fichiers ; Ruff
> `check` + `format --check` verts. Particularité du domaine :
> `GET /api/v1/comments` exige `task_id` en paramètre de requête (422 sans
> lui, 404 tâche inconnue) — jamais de liste globale.
>
> **Engagement jalon 8 honoré** : retouche T045 additive sur `delete_user`
> (`[STEP]` 409 « User {id} still has comments ») — la fonction atteint sa
> **forme finale** : la docstring énonce les deux blocages (organisations,
> commentaires) et la règle SET NULL de l'assignation comme règles
> effectives, sans plus aucune mention différée. Puis T046 : re-exécution
> des tests des jalons 4–7, zéro régression.
>
> Le **graphe relationnel est complet** : 5 domaines, 25 endpoints, les
> 6 arêtes FK du §3 posées et testées. Politique de suppression double
> couche intégrale : blocages 409 amont (users ← organizations ← projects,
> users ← comments), cascade de contenance aval
> projects → tasks → comments — vérifiée par le **premier test à trois
> niveaux du projet** (DELETE du projet via l'API → tâche 404 **et**
> commentaire 404), blocage auteur vérifié dans l'autre sens (409, le user
> et ses commentaires subsistent) — et SET NULL sur l'assignation.

> ✅ **Jalon 9 (seed) validé le 2026-08-27 — Phase 2 close** — gate T055
> complet vert : `make db-revision m="seed_noop_check"` en **contrôle de
> dérive** → révision vide (le seed ne touche pas le schéma), supprimée
> comme prescrit ; `make db-migrate` ; 117 tests pytest (79 integration +
> 38 unit) ; MyPy `--strict` sur 58 fichiers ; Ruff `check` +
> `format --check` verts.
>
> **Seed idempotent par délégation aux services** : `app/scripts/seed.py`
> (Alpha-Scope V3 intégral, jeu constant typé `TypedDict`) fait du
> get-or-create par clé naturelle (D11) dans l'ordre du graphe, et chaque
> création passe par le `create_*` du domaine — les invariants sont
> **structurellement préservés** (double couche D2, hachage bcrypt, jamais
> de re-hachage d'un user existant), aucune écriture ORM parallèle aux
> services. `make db-seed` validé en exécution double réelle : comptages
> identiques (5 users, 2 orgs, 4 projects, 12 tasks, 8 comments), zéro
> doublon, zéro erreur ; idempotence verrouillée par
> `test_seed_idempotence.py` (photographies comptes + clés naturelles
> strictement égales) et préconditions pures du jeu par `test_seed.py`.
>
> **Bilan chiffré de la Phase 2** : 5 domaines, **25 endpoints**, les
> **6 arêtes FK** du §3 posées et testées, **117 tests** pytest,
> **58 fichiers** sous MyPy `--strict`, 5 migrations de domaines (plus le
> renommage `uq` de la convention) empilées sur la baseline
> `f2476b2dee09`, politique de suppression double couche intégrale
> (RESTRICT amont, CASCADE de contenance projects → tasks → comments,
> SET NULL sur l'assignation), seed idempotent en une commande.
> Les jalons 4–9 (T001–T055) sont intégralement cochés.

### Phase 3 — Métadonnées

| # | Jalon | Livrable | Validation |
|---|---|---|---|
| 10 | Topologie | `generate_topology_headers.py` | 0 import non résolu |
| 11 | Structure | `generate_structural_metadata.py` | `TOPOLOGY.yaml` produit |
| 12 | Contrats | `CONTRACTS.md` | Toutes les FK cross-domaines documentées |
| 13 | **Test RAG précoce** | Vectorisation d'un échantillon | Une question cross-domaine remonte les bons chunks |

> Le jalon 13 est un point de contrôle décisif. Si les bons chunks ne remontent
> pas, le format d'annotation doit être corrigé **avant** d'aller plus loin.
> Il est bien moins coûteux de le découvrir sur trois fichiers que sur soixante-dix.

### Phase 4 — Frontend

| # | Jalon | Livrable | Validation |
|---|---|---|---|
| 14 | Squelette | Vite + React + TS + Tailwind, layout, routing | L'app se lance |
| 15 | Couche API | Clients Axios, types TS, hooks TanStack Query | Un GET affiche des données réelles |
| 16 | Pages CRUD | Dashboard, organizations, projects, tasks, comments | CRUD complet depuis l'UI |
| 17 | Intégration | CORS, proxy Vite, Docker Compose unifié | `make up` lance tout |

### Phase 5 — Le tireur

| # | Jalon | Livrable | Validation |
|---|---|---|---|
| 18 | Indexation | Pipeline d'ingestion AST → vecteurs | Le corpus complet est indexé |
| 19 | GraphRAG | Graphe de code + retrieval | Requêtes structurelles correctes |
| 20 | Boucle agentique | Génération + test + auto-correction en sandbox | Taux d'erreur mesuré et décroissant |

---

## 9. Méthode de travail

**Chat web** — cerveau stratégique. On décide, on affine, on rédige les prompts.

**`CLAUDE.md`** — contexte persistant. Claude Code n'a aucune mémoire entre les
sessions ; ce fichier est relu automatiquement à chaque démarrage. Il est mis à
jour à la fin de chaque jalon.

**Claude Code** — exécuteur local. Reçoit des prompts précis et bornés, avec les
contraintes Alpha-Scope rappelées explicitement à chaque fois.

---

## 10. Principes directeurs

À chaque décision, privilégier :

1. La **prévisibilité structurelle** plutôt que la concision
2. La **régularité** plutôt que l'élégance ponctuelle
3. Le **parsable de façon déterministe** plutôt que le clever
4. La **validation précoce** plutôt que l'accumulation avant test

Aucun arrangement arbitraire n'est toléré.
