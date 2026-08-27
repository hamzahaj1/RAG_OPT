# Implementation Plan: Phase 3 — Métadonnées

**Branch**: `002-phase3-metadata` | **Date**: 2026-08-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-phase3-metadata/spec.md`

## Summary

Quatre jalons en ordre strict pour doter le corpus `app/` (phase 2, figée) de
ses métadonnées RAG, sans modifier aucun comportement applicatif :

- **Jalon 10** — `scripts/generate_topology_headers.py` : analyse AST de
  `app/`, résolution complète des imports et alias (R2), graphe d'appels,
  calcul `weight`/`tier` (sémantique figée R1), insertion des en-têtes `[RAG]`
  sur toutes les fonctions des `services.py` et `router.py` des cinq domaines.
- **Jalon 11** — `scripts/generate_structural_metadata.py` : blocs `[MODEL]`
  sur `models.py`, `[SCHEMA]` sur `schemas.py`, production de `TOPOLOGY.yaml`
  à la racine en sérialisation déterministe (R4).
- **Jalon 12** — `CONTRACTS.md` à la racine : les 6 arêtes FK cross-domaines,
  politique de suppression, double couche, invariants — dérivé des migrations
  et docstrings existantes.
- **Jalon 13** — test RAG précoce : chunking par marqueurs de 3 fichiers
  annotés, vectorisation locale (R5), 2 questions cross-domaines, constat
  documenté ; en cas d'échec, correction du format **avant** généralisation.

Toute l'insertion est un remplacement délimité idempotent (R3) piloté par les
cibles `make rag-annotate` / `make rag-check` (R7). Chaque jalon est clos par
un gate complet vert puis un commit (R10).

## Technical Context

**Language/Version**: Python 3.14 local (contrainte projet `>=3.11`) — les
scripts n'utilisent que la stdlib (`ast`, `pathlib`, `re`) plus PyYAML ;
outillage jalon 13 : fastembed + numpy (repli venv 3.12 acté en R5).

**Primary Dependencies**: stdlib `ast` (analyse et graphe) ; `pyyaml` (dump
`TOPOLOGY.yaml`) ; `fastembed` + `numpy` (jalon 13 uniquement) — toutes en
groupe **dev** Poetry, `app/` n'acquiert aucune dépendance.

**Storage**: N/A — aucune écriture en base ; artefacts = fichiers annotés,
`TOPOLOGY.yaml`, `CONTRACTS.md`, `jalon13-constat.md`.

**Testing**: pytest (suite phase 2 : 117 tests, inchangés — preuve de
non-régression) + tests unitaires dédiés de l'outillage sous `tests/unit/`
(résolution d'alias, calcul weight/tier, idempotence du remplacement,
déterminisme du dump) ; MyPy `--strict` et Ruff sur tout nouveau fichier.

**Target Platform**: Linux local (Fedora), exécution via `poetry run` ;
PostgreSQL/Podman non requis par les scripts (l'analyse est statique).

**Project Type**: outillage AST + documentation — deux scripts CLI, deux
artefacts racine, un rapport de jalon.

**Performance Goals**: corpus de 33 fichiers / ~25 endpoints — exécution
complète de `rag-annotate` en secondes ; aucun objectif de débit.

**Constraints**: idempotence stricte (deux exécutions = diff vide, SC-002) ;
déterminisme octet pour octet de `TOPOLOGY.yaml` (R4, R6) ; zéro import non
résolu, échec explicite sinon (FR-007) ; zéro modification de comportement de
`app/` (FR-006) — gate complet vert **après** annotation (R10) ; Standard
Alpha-Scope V3 intégral sur les scripts eux-mêmes, qui restent hors corpus
(R8) ; piège heredoc `(?:'|")` (R9).

**Scale/Scope**: 5 domaines × (`services.py` + `router.py`) à annoter `[RAG]`
(~55 fonctions), 5 `models.py` + 5 `schemas.py` en `[MODEL]`/`[SCHEMA]`,
6 arêtes FK à documenter, échantillon de 3 fichiers à vectoriser.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution v1.0.0 (projection de CLAUDE.md — en cas de conflit, CLAUDE.md
gagne) :

- **I. Prévisibilité structurelle** : formats d'annotation fixes à champs
  ordonnés (§ Formats), ancrage d'insertion déterministe — PASS.
- **II. Régularité** : le même bloc `[RAG]` sur chacune des ~55 fonctions,
  le même patron `[MODEL]`/`[SCHEMA]` sur les 10 fichiers — aucune exception
  par domaine — PASS.
- **III. Parsable de façon déterministe** : marqueurs appariés ouvrant/fermant
  (R3), tri ASCII partout (R6, R4), analyse AST sans exécution du code — PASS.
- **IV. Validation précoce** : le jalon 13 teste le format sur 3 fichiers
  avant toute généralisation (raison d'être de la phase) ; `rag-check` au
  gate dès le jalon 10 — PASS.
- **Standard V3** : les deux scripts et `rag_probe.py` le suivent
  intégralement (zones 0/A/B/C, tri ASCII des fonctions, marqueurs) — PASS.
- **Stack** : aucune substitution ; ajouts uniquement en groupe dev (pyyaml,
  fastembed, numpy) — la stack applicative §4 est intouchée — PASS.
- **Gouvernance** : un commit par gate, amendements en commits distincts
  (R10) — PASS.

Aucune violation → **Complexity Tracking vide**.

## Project Structure

### Documentation (this feature)

```text
specs/002-phase3-metadata/
├── spec.md              # Spécification (commitée, gate de revue passé)
├── plan.md              # Ce fichier
├── research.md          # Phase 0 — décisions R1–R10
├── jalon13-constat.md   # Rapport du test RAG précoce (produit au jalon 13)
└── tasks.md             # Découpage en tâches (étape suivante — hors de ce tour)
```

`data-model.md`, `contracts/`, `quickstart.md` : **N/A** — la phase ne crée
aucune entité persistée ni endpoint ; la documentation contractuelle du
jalon 12 est un artefact racine (`CONTRACTS.md`), pas un artefact de spec.

### Source Code (repository root)

```text
scripts/                              # Outillage V3, HORS corpus (R8)
├── generate_topology_headers.py      # Jalon 10
├── generate_structural_metadata.py   # Jalon 11
└── rag_probe.py                      # Jalon 13 — chunking + embed + top-k

app/                                  # CORPUS — annoté, jamais modifié en comportement
├── core/{config,database}.py         # Analysés (graphe) ; non annotés par les scripts
├── domains/*/services.py             # ← en-têtes [RAG] (jalon 10)
├── domains/*/router.py               # ← en-têtes [RAG] (jalon 10)
├── domains/*/models.py               # ← bloc [MODEL] (jalon 11)
├── domains/*/schemas.py              # ← bloc [SCHEMA] (jalon 11)
└── scripts/seed.py                   # Analysé (source d'arêtes CORE) ; non annoté

TOPOLOGY.yaml                         # Jalon 11 — racine, généré, commité
CONTRACTS.md                          # Jalon 12 — racine, rédigé, commité
Makefile                              # + cibles rag-annotate / rag-check (R7)
tests/unit/                           # + tests de l'outillage (voir jalons)
```

**Structure Decision** : structure existante inchangée — la phase **ajoute**
trois scripts hors corpus, deux artefacts racine et deux cibles Makefile ;
elle **annote** `app/` sans y créer ni déplacer aucun fichier.

## Formats d'annotation (référence normative des jalons 10–11)

Décision R3 instanciée. Les trois blocs partagent les mêmes règles : marqueurs
appariés en commentaires `#`, champs en ordre fixe, listes triées ASCII et
séparées par `, ` ; liste vide → `none` ; noms de fonctions qualifiés relatifs
au corpus (`domaine.module.fonction`, ex. `users.services.create_user` ;
noyau : `core.database.get_db` ; seed : `scripts.seed.<fn>`).

### En-tête `[RAG]` (Zone 0 — services.py, router.py)

Ancrage : bloc inséré **immédiatement au-dessus** de la première ligne de la
définition (le premier décorateur s'il y en a, sinon `def`/`async def`),
après une ligne vide. Remplacement : tout bloc `# [RAG]` … `# [/RAG]`
existant à cet ancrage est intégralement remplacé.

```python
# [RAG]
# signature: create_user(db: AsyncSession, data: UserCreate) -> User
# weight: 4
# tier: CORE
# calls: users.services._hash_password
# called_by: scripts.seed._seed_users, users.router.create_user
# reads: users
# mutates: users
# [/RAG]
async def create_user(db: AsyncSession, data: UserCreate) -> User:
```

Champs — ordre fixe : `signature` (nom + paramètres typés + retour, dérivés
de l'AST), `weight` (entier, R1), `tier` (`LEAF` | `CORE` | `CRITICAL_CORE`),
`calls` / `called_by` (noms qualifiés triés), `reads` / `mutates` (noms de
tables triés).

### Bloc `[MODEL]` (models.py — niveau fichier)

Ancrage : immédiatement **après** la ligne `# [FILE]`, avant la docstring de
module. Un bloc par entité du fichier (phase 2 : une entité par fichier).

```python
# [MODEL]
# entity: User
# table: users
# columns: created_at, email, full_name, hashed_password, id, role, updated_at
# fks: none
# referenced_by: comments.author_id -> RESTRICT, organizations.owner_id -> RESTRICT, tasks.assignee_id -> SET NULL
# [/MODEL]
```

Champs : `entity`, `table`, `columns` (triées), `fks`
(`colonne -> table.colonne [politique]`, triées), `referenced_by` (arêtes
entrantes avec politique `ondelete`, triées — dérivées du graphe complet des
modèles, c'est le signal RAG des questions de suppression).

### Bloc `[SCHEMA]` (schemas.py — niveau fichier)

Même ancrage que `[MODEL]`.

```python
# [SCHEMA]
# domain: users
# schemas: UserCreate(BaseModel), UserRead(BaseModel), UserUpdate(BaseModel)
# entity: User
# [/SCHEMA]
```

Champs : `domain`, `schemas` (classes triées avec leur base directe),
`entity` (modèle SQLAlchemy correspondant du domaine).

### `TOPOLOGY.yaml` (racine)

```yaml
functions:
  core.database.get_db:
    called_by: [comments.router.create_comment, ...]   # triée
    calls: []
    file: app/core/database.py
    mutates: []
    reads: []
    tier: CRITICAL_CORE
    weight: 27
```

Sérialisation R4 : `safe_dump(sort_keys=True)`, listes pré-triées, aucun
horodatage, UTF-8, LF, newline final unique.

## Déroulé par jalon

### Jalon 10 — Topologie (`generate_topology_headers.py`)

1. Découverte : `sorted(Path("app").rglob("*.py"))` (R6).
2. Passe 1 — parse AST de chaque fichier, table des imports/alias par module
   (R2.2) ; échec explicite sur tout symbole non résolu (R2.3).
3. Passe 2 — graphe d'appels : appels directs, appels via alias, arêtes
   `Depends(f)` (R2.1) ; `reads`/`mutates` par motifs SQLAlchemy (R2).
4. Calcul `weight`/`tier` (R1) sur le graphe complet.
5. Insertion des blocs `[RAG]` (format ci-dessus) sur toutes les fonctions
   des `services.py` et `router.py` des 5 domaines — remplacement délimité.
6. Makefile : cible `rag-annotate` (partielle : ce script) + `rag-check`.
7. Tests unitaires : résolution d'alias, règle `Depends`, weight/tier sur un
   mini-corpus fixture, idempotence (double exécution → arbre identique).

**Gate 10** : 0 import non résolu ; en-têtes présents et exacts sur les
5 domaines (SC-001) ; `rag-check` vert ; pytest (117 + nouveaux), MyPy
`--strict`, Ruff verts **après annotation** ; commit de gate.

### Jalon 11 — Structure (`generate_structural_metadata.py`)

1. Réutilise l'analyse du jalon 10 (module partagé ou ré-analyse — décision
   de tâches) ; blocs `[MODEL]` et `[SCHEMA]` sur les 10 fichiers cibles.
2. Production de `TOPOLOGY.yaml` (R4) — graphe complet du corpus, y compris
   fonctions non porteuses d'en-tête (`core/`, `seed`, `main`).
3. `rag-annotate` prend sa forme finale : les deux scripts dans l'ordre.
4. Tests : déterminisme (double génération → fichiers identiques octet pour
   octet), présence des 10 blocs.

**Gate 11** : `TOPOLOGY.yaml` produit et identique entre deux générations
(SC-002) ; `rag-check` vert ; suite complète verte ; commit de gate.

### Jalon 12 — Contrats (`CONTRACTS.md`)

Rédaction (pas de génération) depuis les sources de vérité : migrations
`1d70e9de6246`, `677e300dd994`, `443e75f588d9`, `3b55d9e3f2bf`, docstrings
des services, `data-model.md` de la phase 2. Pour chacune des 6 arêtes :
politique de suppression (RESTRICT / CASCADE / SET NULL), vérification double
couche (409 applicatif + contrainte DB — ou dérogation actée : SET NULL de
l'assignation, DB seule), invariants métier portés. Aucune règle réinventée
(FR-014).

**Gate 12** : 6 arêtes documentées, zéro contradiction avec le modèle de
données (SC-004) ; `rag-check` vert (aucune dérive d'annotation) ; suite
verte ; commit de gate.

### Jalon 13 — Test RAG précoce (`scripts/rag_probe.py`)

1. Échantillon : `app/domains/users/services.py`,
   `app/domains/organizations/services.py`, `app/core/database.py` (FR-015 —
   le troisième est volontairement **non annoté** par les scripts : le
   chunking doit tenir sur ses seuls marqueurs de base, edge case de la spec).
2. Chunking par marqueurs : un chunk = un bloc `[RAG]` + sa fonction
   (délimitation par les ancrages du format) ; boilerplate d'imports exclu
   via `[CODE_START]` (FR-016).
3. Vectorisation fastembed + index numpy en mémoire (R5), top-k = 5.
4. Questions de contrôle (au moins 2) : Q1 « que se passe-t-il quand on
   supprime un utilisateur ? » — attendus : chunk `delete_user` + métadonnées
   d'arêtes concernées (organisations, commentaires, assignation) ;
   Q2 cross-domaine (candidate : « qui a le droit de posséder une
   organisation ? » ou « comment obtient-on une session de base de
   données ? » — figée dans tasks.md).
5. Constat écrit dans `jalon13-constat.md` : questions, chunks remontés,
   classement, verdict (FR-018). **Si échec** : correction du format
   d'annotation (retour jalons 10–11), régénération, test rejoué — avant
   toute généralisation.

**Gate 13** : bons chunks dans le top-k pour chaque question, constat
documenté (SC-005) ; `rag-check` vert ; suite verte ; commit de gate —
**clôture de la phase 3**.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

Aucune violation — table vide.
