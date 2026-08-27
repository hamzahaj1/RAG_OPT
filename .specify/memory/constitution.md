# Alpha-Scope RAG Constitution

> Projection normative de `CLAUDE.md` (document de référence unique du projet).
> Ce document ne crée **aucun principe nouveau** : il reformule, au format
> constitution de Spec Kit, les règles déjà actées dans la charte.
> **En cas de conflit, `CLAUDE.md` gagne** — la constitution est corrigée,
> jamais l'inverse.

## Core Principles

### I. Prévisibilité structurelle plutôt que concision

(Charte §10.1.) Toute décision de code privilégie la structure prévisible sur
la forme courte. Le livrable réel du projet est une base de code dont la
géométrie est si régulière qu'un pipeline RAG peut la découper, l'indexer et
la raisonner sans ambiguïté (charte §1) — une concision qui casse cette
prévisibilité est une régression, pas une amélioration.

### II. Régularité plutôt qu'élégance ponctuelle

(Charte §10.2.) Un motif appliqué uniformément partout vaut mieux qu'une
solution localement plus élégante. Le code doit être **simultanément** réel
et moderne (patterns qu'un senior FastAPI reconnaît) et géométriquement
parfait (charte §2) — test permanent : *est-ce qu'un senior FastAPI
embaucherait quelqu'un qui a écrit ça ?*

### III. Parsable de façon déterministe plutôt que clever

(Charte §10.3.) Le code est écrit pour être analysé par AST et découpé par
marqueurs de façon déterministe. Toute astuce (« clever ») qui rend le
parsing ambigu est proscrite, même si elle est idiomatique ailleurs.

### IV. Validation précoce plutôt qu'accumulation avant test

(Charte §10.4.) Un jalon = un prompt = un livrable vérifiable, validé avant
le suivant (charte §8). Les points de contrôle décisifs (ex. jalon 13, test
RAG précoce) sont exécutés au plus tôt, sur le plus petit périmètre
probant — jamais après accumulation.

**Clause transversale (charte §10) : aucun arrangement arbitraire n'est
toléré.**

## Standard Alpha-Scope V3 (charte §6 — non négociable)

S'applique à **toutes** les fonctions de **tous** les fichiers. Aucune
exception, aucun raccourci.

- **Zone 0 — En-tête `[RAG]`** : bloc machine-readable avant la signature —
  `signature`, `weight`, `tier` (`CRITICAL_CORE` | `CORE` | `LEAF`),
  `calls`, `called_by`, `reads`, `mutates`.
- **Zone A — Contrat** : arguments triés, `db` toujours en première
  position, docstring documentant règles métier, invariants et cas
  limites — jamais une reformulation du nom.
- **Zone B — Empreinte** : toutes les variables locales déclarées, triées
  et typées explicitement, avant toute logique, dans le bloc balisé
  `─── ZONE DE DÉCLARATION DES VARIABLES ───`.
- **Zone C — Algorithme** : étapes `[STEP]` portant chacune une
  postcondition `→` ; borne de 25 à 30 lignes mesurée du premier `[STEP]`
  à la dernière ligne (zones A et B non bornées).
- **Ordre alphabétique déterministe** : dans un même fichier, fonctions
  triées par ordre ASCII strict de leur nom (l'underscore précède les
  minuscules) ; aucun regroupement par logique métier.
- **Marqueurs de chunking** : `[FILE]` en tête de fichier, `[CODE_START]`
  après le bloc d'imports.
- **Annotations générées, jamais manuelles** (charte §7) : `[RAG]`,
  `[MODEL]`, `[SCHEMA]` sont produites exclusivement par les scripts
  d'analyse AST (`generate_topology_headers.py`,
  `generate_structural_metadata.py`).

## Stack technique (charte §4 — inflexible)

Aucune substitution sans décision explicite.

- **Backend** : Python 3.11+ (typage statique strict obligatoire), FastAPI
  asynchrone, SQLAlchemy 2.0 async avec `asyncpg`, PostgreSQL 16, Alembic,
  Pydantic V2, Poetry, Ruff, MyPy, Pytest.
- **Frontend** : React 18+ avec TypeScript, Vite, TailwindCSS, TanStack
  Query, Zustand, React Hook Form + Zod.
- **Infrastructure** : Docker Compose (PostgreSQL, backend, frontend,
  Adminer) — exécuté localement via Podman (charte §4 bis).
- **Étape 2** : GraphRAG, DeepSeek-R1.

Les décisions d'environnement locales (charte §4 bis) — Podman, Python
local 3.14, Alembic à `sqlalchemy.url` neutralisée, `make db-revision`
obligatoire, corpus RAG = `app/` exclusivement — sont actées et ne se
renégocient que par décision explicite.

## Governance

- **`CLAUDE.md` est le document de référence unique** ; la présente
  constitution en est une projection. Tout conflit se résout en faveur de
  `CLAUDE.md`, et la constitution est amendée en conséquence.
- **Un commit par gate validé (minimum obligatoire)**, sur la branche de la
  phase en cours ; **un jalon n'est clos qu'une fois commité** (charte
  §4 bis).
- **Les amendements de gouvernance** (`CLAUDE.md`, constitution, specs)
  sont commités dès leur rédaction, en commits de documentation distincts
  des commits de gate.
- Toute évolution de sémantique figée (ex. `weight`/`tier`) est une
  décision de gouvernance, pas un choix d'implémentation.

**Version**: 1.0.0 | **Ratified**: 2026-08-27 | **Last Amended**: 2026-08-27
