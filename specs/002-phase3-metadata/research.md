# Research : Phase 3 — Métadonnées

**Branch**: `002-phase3-metadata` | **Date**: 2026-08-27 | **Spec**: [spec.md](spec.md)

Phase 0 du plan. Chaque décision suit le format : Décision / Justification /
Alternatives rejetées. Les décisions **figées en amont** (spec, Assumptions ;
prompt de gouvernance) sont reprises telles quelles et marquées ⚑ — elles ne
sont pas rediscutées ici, seulement consignées comme exigences d'entrée.

---

## R1 ⚑ — Sémantique `weight` / `tier` (figée)

**Décision** (verbatim, spec Assumption 1 et FR-008/FR-009) :

- `weight` = appels entrants + appels sortants dans le graphe résolu.
- `LEAF` = 0 appel entrant hors de son routeur.
- `CORE` = référencé par au moins un service ou le seed (`app/scripts/seed.py`).
- `CRITICAL_CORE` = `get_db`, `settings`, et toute fonction référencée par
  3 domaines ou plus.

Toute évolution de cette sémantique est une **décision de gouvernance**, pas un
choix d'implémentation.

**Précisions d'application** (dérivées, sans étendre la sémantique) :

- Le « graphe résolu » est celui du corpus `app/` exclusivement (R8).
- La classification est évaluée dans l'ordre `CRITICAL_CORE` → `CORE` → `LEAF` ;
  une fonction éligible à deux niveaux prend le plus élevé (edge case de la
  spec : jamais diluée dans un niveau inférieur).
- « Référencée par N domaines » compte les **domaines appelants distincts**
  (`users`, `organizations`, `projects`, `tasks`, `comments`, plus `core` et
  `app.scripts` comme modules hors-domaines) — pas les sites d'appel.

## R2 — Règles de résolution du graphe d'appels

**Décision** : le graphe encode la **réalité d'exécution**, avec trois règles
explicites :

1. **Dépendances FastAPI** : `Depends(f)` dans une signature de routeur crée
   une **arête entrante vers `f`** (le framework appelle `f` à chaque requête).
   C'est ainsi que `get_db` acquiert ses arêtes entrantes depuis les 25
   endpoints. Règle documentée du graphe, pas un cas particulier silencieux.
2. **Alias de modules** : les appels via alias sont résolus vers leur cible
   réelle — `import app.domains.users.services as s ; s.create_user(...)` crée
   une arête vers `app.domains.users.services.create_user`. Idem pour
   `from ... import x as y`. La table des alias est construite par fichier à
   partir des nœuds `Import`/`ImportFrom` de l'AST.
3. **Échec explicite** : tout nom appelé qui ne se résout ni vers le corpus,
   ni vers un import externe identifié (stdlib, dépendances) fait échouer le
   script avec un message nommant fichier, ligne et symbole — jamais un
   en-tête silencieusement incomplet (FR-007, edge case de la spec).

`reads` / `mutates` sont dérivés du même AST : `reads` = tables des modèles
apparaissant dans les constructions de lecture (`select(Model)`, jointures) ;
`mutates` = tables des instances passées à `db.add`/`db.delete` ou mutées par
affectation d'attribut avant `commit`. Les appels traversants héritent en
lecture directe uniquement (pas de fermeture transitive : l'en-tête décrit la
fonction, le graphe fournit la transitivité).

**Justification** : sans la règle `Depends`, `get_db` serait un faux `LEAF` —
contradiction directe avec la sémantique figée qui le nomme `CRITICAL_CORE`.
Sans résolution d'alias, le comptage « 3+ domaines » serait faux.

**Alternatives rejetées** : graphe purement lexical (arêtes uniquement sur
appels directs) — simple mais faux à l'exécution ; résolution dynamique par
import du module (risque d'effets de bord, non déterministe).

## R3 — Insertion idempotente : blocs délimités par marqueurs appariés

**Décision** : chaque annotation générée est un **bloc de commentaires délimité
par une paire de marqueurs ouvrant/fermant** (`# [RAG]` … `# [/RAG]`,
`# [MODEL]` … `# [/MODEL]`, `# [SCHEMA]` … `# [/SCHEMA]`). La régénération
**remplace intégralement** le bloc existant (suppression de tout ce qui se
trouve entre les marqueurs inclus, réinsertion) ; s'il n'existe pas, insertion
au point d'ancrage déterministe. Le format exact (champs, ordre, ancrage) est
spécifié dans le plan (§ Formats d'annotation).

**Justification** : le remplacement délimité est la seule forme qui garantit
FR-002 (deux exécutions successives = diff vide) sans état externe : le bloc
est sa propre frontière. Un marqueur fermant rend le retrait non ambigu même
si le contenu du bloc change de nombre de lignes.

**Alternatives rejetées** : bloc reconnu par préfixe de commentaire sans
fermeture (fragile si un commentaire manuel suit) ; en-têtes dans les
docstrings (mélange contrat humain / métadonnées machine, viole la Zone A).

## R4 — `TOPOLOGY.yaml` : sérialisation déterministe spécifiée

**Décision** : exigence du plan, pas détail d'implémentation —

- dump via `yaml.safe_dump(..., sort_keys=True, allow_unicode=True,
  default_flow_style=False)` ;
- toutes les **listes triées explicitement** (ordre lexicographique ASCII des
  noms qualifiés) avant sérialisation — `sort_keys` ne trie que les clés ;
- clés de premier niveau = noms qualifiés complets des fonctions ;
- aucun horodatage, aucun champ dépendant de l'environnement ; encodage UTF-8,
  fins de ligne LF, newline final unique.

Dépendance : `pyyaml` ajoutée au groupe **dev** de Poetry (outillage hors
corpus ; `app/` n'en dépend pas).

**Justification** : SC-002 exige l'identité octet pour octet entre deux
générations ; chaque source de non-déterminisme (ordre des dict, des listes,
horodatage) doit être fermée par construction.

**Alternatives rejetées** : JSON (lisibilité moindre pour un artefact de
référence, la charte nomme `TOPOLOGY.yaml`) ; dump YAML par défaut (ordre
d'insertion, non trié).

## R5 — Outillage du jalon 13 : le plus simple qui prouve le format

**Décision** : **`fastembed`** (modèle
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`) + **`numpy`**
— embeddings locaux ONNX sans service ni GPU, index = matrice en mémoire,
similarité cosinus, **top-k = 5** brut.

**Justification (une ligne)** : embedding 100 % local et multilingue (les
questions de contrôle sont en français, le corpus mêle français et anglais),
zéro infrastructure — le jalon teste le **format d'annotation**, pas un moteur
de retrieval.

**Cadre** : script `scripts/rag_probe.py` (Standard V3, hors corpus),
dépendances dans le groupe dev. **Pas de base vectorielle, pas de framework
RAG** — ils arrivent en phase 5 (jalons 18–19). Constat documenté dans
`specs/002-phase3-metadata/jalon13-constat.md` (questions, chunks remontés,
classement, verdict).

**Risque identifié** : disponibilité des wheels `onnxruntime` pour le Python
local 3.14. Repli acté si absence : venv jetable Python 3.12 dédié au seul
`rag_probe.py` (outillage hors corpus, hors environnement Poetry du projet) —
le corpus et les scripts d'annotation ne bougent pas.

**Alternatives rejetées** : `sentence-transformers` (tire PyTorch — lourd pour
trois fichiers) ; API d'embedding distante (dépendance réseau, non
reproductible localement) ; chroma/qdrant/LangChain (infrastructure de
phase 5, contraire au « plus simple qui prouve le format »).

## R6 — Ordre de traitement déterministe des fichiers

**Décision** : les deux scripts découvrent les fichiers par
`sorted(Path("app").rglob("*.py"))` — tri lexicographique ASCII des chemins
POSIX relatifs — et les traitent dans cet ordre. Aucune dépendance à l'ordre
du système de fichiers.

**Justification** : diffs stables entre exécutions et entre machines ;
condition nécessaire de SC-002 et du contrôle `rag-check`.

## R7 ⚑ — Cibles Makefile `rag-annotate` / `rag-check` (figées)

**Décision** (spec Assumption 2, FR-003) :

- `rag-annotate` : exécute `generate_topology_headers.py` **puis**
  `generate_structural_metadata.py` (l'ordre importe : la structure sérialise
  le graphe que la topologie a résolu).
- `rag-check` : `rag-annotate` puis
  `git diff --exit-code -- app/ TOPOLOGY.yaml` — échoue si l'annotation
  n'était pas à jour, sur le modèle du contrôle de dérive Alembic
  (`make db-revision` → révision vide).

## R8 ⚑ — Frontière du corpus (figée)

**Décision** (CLAUDE.md §4 bis, spec Assumption 3) : le corpus analysé et
annoté est **`app/` exclusivement** — `app/scripts/seed.py` en fait partie
(c'est le « seed » de la sémantique `CORE`). `scripts/`, `.specify/`,
`specs/`, `tests/` et `alembic/` sont hors corpus ; les scripts de `scripts/`
suivent néanmoins le Standard V3 intégral.

## R9 ⚑ — Piège heredoc bash (figé)

**Décision** (charte §7, spec Assumption 5) : pendant tout le développement
des scripts, le motif regex `["\']` est **proscrit** dans les heredocs bash —
forme obligatoire : `(?:'|")`.

## R10 ⚑ — Gouvernance des gates (figée)

**Décision** (FR-004, FR-019, SC-003, SC-006) : chaque jalon 10 → 13 est clos
par un gate complet vert — pytest, MyPy `--strict`, Ruff `check` +
`format --check`, **contrôle d'idempotence `rag-check`** (dès le jalon 10) —
suivi d'un **commit de gate** sur `002-phase3-metadata`. Le gate se prouve
**après annotation** : les en-têtes sont des commentaires, mais c'est vérifié
à chaque gate, jamais supposé. Amendements de gouvernance en commits
distincts. La phase ne modifie **aucun comportement** de `app/` (FR-006).
