# Tasks: Phase 3 — Métadonnées

**Input**: Design documents from `/specs/002-phase3-metadata/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md)
(`data-model.md`, `contracts/`, `quickstart.md` : N/A — acté au plan).

**Numérotation** : suite globale du projet — la phase 2 s'est close sur T055,
la phase 3 commence à **T056** (CLAUDE.md référence les gates par leur T-id).

**Organisation** : groupement par **jalon**, ordre strict 10 → 13 — un jalon
n'ouvre que lorsque le précédent est clos (gate vert + commit). Les jalons
correspondent aux user stories US1–US4 de la spec.

## Format: `[ID] [P?] [Jalon] Description`

- **[P]** : parallélisable à l'intérieur du jalon (fichiers distincts, sans
  dépendance) — jamais entre jalons.
- Chemins exacts dans chaque description.

**Hors périmètre (aucune tâche n'y touche)** : généralisation de l'indexation
au corpus complet (jalon 18, phase 5), frontend (phase 4), toute modification
fonctionnelle de `app/` — la phase annote, elle ne change aucun comportement
(FR-006).

---

## Jalon 10 — Topologie (US1, P1) 🎯

**Goal** : graphe d'appels complet de `app/`, en-têtes `[RAG]` exacts sur
toutes les fonctions des `services.py` et `router.py` des cinq domaines.

**Independent Test** : exécution sur le code de la phase 2 — zéro import non
résolu, en-têtes complets sur les 5 domaines, double exécution = diff vide.

- [x] **T056** [J10] **Module d'analyse partagé** `scripts/corpus_analysis.py`
      (Standard V3 intégral, hors corpus — **avant les deux générateurs**,
      arbitrage acté) : découverte `sorted(Path("app").rglob("*.py"))` (R6) ;
      parse AST ; table des imports/alias par module (R2.2) ; résolution avec
      échec explicite nommant fichier, ligne, symbole (R2.3) ; graphe
      d'appels — appels directs, via alias, arêtes `Depends(f)` (R2.1) ;
      `reads`/`mutates` par motifs SQLAlchemy (R2) ; calcul `weight`/`tier`
      (R1, ordre `CRITICAL_CORE` → `CORE` → `LEAF`). API pure : le module
      analyse et retourne, il n'écrit aucun fichier.
- [x] **T057** [P] [J10] Tests unitaires du module dans
      `tests/unit/test_corpus_analysis.py`, sur mini-corpus fixture :
      résolution d'alias (`import ... as s ; s.f()`), règle `Depends`
      (`get_db` reçoit ses arêtes entrantes), weight/tier conformes à R1
      (cas limites : LEAF jamais appelé hors routeur, CRITICAL_CORE 3+
      domaines non dilué), symbole non résolu → erreur nommée, jamais un
      en-tête incomplet.
- [x] **T058** [J10] Générateur `scripts/generate_topology_headers.py`
      (consommateur de `corpus_analysis`) : blocs `# [RAG]` … `# [/RAG]` au
      format normatif du plan (§ Formats — champs en ordre fixe, listes
      triées ASCII, `none` si vide) ; ancrage immédiatement au-dessus du
      premier décorateur ou du `def` ; **remplacement délimité** du bloc
      existant (R3) ; cibles = **toutes les fonctions du corpus hors
      `models.py`/`schemas.py`** : les 10 fichiers `services.py` +
      `router.py` des cinq domaines, `app/core/config.py`,
      `app/core/database.py`, `app/main.py` et `app/scripts/seed.py`
      (périmètre étendu par amendement de gouvernance — CLAUDE.md §7).
- [x] **T059** [P] [J10] Tests du générateur dans
      `tests/unit/test_topology_headers.py` : format et ancrage du bloc,
      idempotence (double exécution sur fixture → contenu strictement
      identique), remplacement (un bloc périmé ne survit pas, aucune
      accumulation), fichiers hors cible intouchés.
- [x] **T060** [J10] Makefile : cible `rag-annotate` (forme jalon 10 : la
      topologie seule) et cible `rag-check` = `rag-annotate` puis
      `git diff --exit-code -- app/ TOPOLOGY.yaml` (R7, modèle du contrôle
      de dérive Alembic) ; entrées `help` correspondantes.
- [x] **T061** [J10] Exécution réelle sur `app/` : zéro import non résolu ;
      en-tête complet sur 100 % des fonctions du corpus hors
      `models.py`/`schemas.py` — services et routeurs des 5 domaines,
      `core/config.py`, `core/database.py`, `main.py`, `scripts/seed.py`
      (SC-001, périmètre étendu) ; contrôles de véracité ponctuels contre le
      code — **`get_db` est `CRITICAL_CORE` avec `called_by` couvrant les
      5 domaines** (via `Depends`), `delete_user` avec `reads`
      organizations/comments et ses appelants réels.
- [x] **T062** [J10] **GATE 10 — complet, APRÈS annotation** :
      `make rag-check` vert (idempotence prouvée) ; pytest intégral (les
      117 tests de la phase 2 + T057/T059) ; MyPy `--strict` ; Ruff
      `check` + `format --check` (R10, SC-003).
- [x] **T063** [J10] **COMMIT de gate du jalon 10** sur
      `002-phase3-metadata` — le jalon n'est clos qu'une fois commité
      (FR-019).

**Checkpoint** : topologie exacte et idempotente — le jalon 11 peut ouvrir.

---

## Jalon 11 — Structure (US2, P2)

**Goal** : `[MODEL]`/`[SCHEMA]` sur les 10 fichiers de modèles et schémas,
`TOPOLOGY.yaml` déterministe à la racine.

**Independent Test** : deux générations successives → `TOPOLOGY.yaml` existe,
décrit le graphe complet, fichiers identiques octet pour octet.

- [x] **T064** [J11] Dépendance dev : `pyyaml` au groupe dev de Poetry (R4) —
      `app/` n'acquiert aucune dépendance.
- [x] **T065** [J11] Générateur `scripts/generate_structural_metadata.py`
      (consommateur de `corpus_analysis`) : blocs `# [MODEL]` … `# [/MODEL]`
      sur les 5 `models.py` (entity, table, columns triées, fks,
      `referenced_by` avec politiques `ondelete` — le signal RAG des
      questions de suppression) et `# [SCHEMA]` … `# [/SCHEMA]` sur les 5
      `schemas.py`, ancrés après la ligne `# [FILE]` (formats du plan) ;
      production de `TOPOLOGY.yaml` à la racine — graphe complet, y compris
      fonctions sans en-tête (`core/`, `scripts.seed`, `main`) —
      sérialisation R4 : `safe_dump(sort_keys=True)`, listes pré-triées,
      aucun horodatage, UTF-8, LF, newline final unique.
- [x] **T066** [P] [J11] Tests dans `tests/unit/test_structural_metadata.py` :
      format et ancrage des blocs sur fixture, idempotence du remplacement,
      double génération de `TOPOLOGY.yaml` → identité octet pour octet.
- [x] **T067** [J11] Makefile : `rag-annotate` prend sa **forme finale** —
      topologie **puis** structure (l'ordre importe : la structure sérialise
      le graphe résolu par la topologie, R7).
- [x] **T068** [J11] Exécution réelle : les 10 blocs posés sur les 5
      domaines ; `TOPOLOGY.yaml` produit à la racine ; double génération
      vérifiée identique (`cmp`) (SC-002).
- [x] **T069** [J11] **GATE 11 — complet, APRÈS annotation** :
      `make rag-check` vert ; pytest intégral ; MyPy `--strict` ; Ruff
      `check` + `format --check`.
- [x] **T070** [J11] **COMMIT de gate du jalon 11** (inclut `TOPOLOGY.yaml`).

**Checkpoint** : couverture d'annotation complète des 4 fichiers de chaque
domaine + index structurel global — le jalon 12 peut ouvrir.

---

## Jalon 12 — Contrats (US3, P3)

**Goal** : `CONTRACTS.md` à la racine — les 6 arêtes FK cross-domaines,
dérivées des sources de vérité, sans réinvention.

**Independent Test** : les 6 arêtes du graphe (CLAUDE.md §3) documentées,
chaque affirmation concordant avec le modèle de données de la phase 2.

- [x] **T071** [J12] Rédiger `CONTRACTS.md` (racine) : pour chacune des 6
      arêtes — `organizations.owner_id → users.id`,
      `projects.organization_id → organizations.id`,
      `tasks.project_id → projects.id`, `tasks.assignee_id → users.id`,
      `comments.task_id → tasks.id`, `comments.author_id → users.id` — la
      politique de suppression (RESTRICT / CASCADE / SET NULL), la
      vérification **double couche** (refus applicatif 409 + contrainte DB ;
      dérogation actée : SET NULL de l'assignation porté par la DB seule) et
      les invariants métier portés. Sources exclusives : migrations
      `1d70e9de6246`, `677e300dd994`, `443e75f588d9`, `3b55d9e3f2bf`,
      docstrings des services, `specs/001-phase2-domains/data-model.md`
      (FR-014 — aucune règle réinventée).
- [x] **T072** [J12] Confrontation systématique, arête par arête, de
      `CONTRACTS.md` contre `data-model.md` et les migrations : zéro
      contradiction (SC-004) ; écarts éventuels corrigés côté
      `CONTRACTS.md`, jamais côté sources.
- [x] **T073** [J12] **GATE 12** : `make rag-check` vert (aucune dérive
      d'annotation) ; pytest intégral ; MyPy `--strict` ; Ruff `check` +
      `format --check`.
- [x] **T074** [J12] **COMMIT de gate du jalon 12** (inclut `CONTRACTS.md`).

**Checkpoint** : la documentation de référence des questions cross-domaines
existe — le jalon 13 peut ouvrir.

---

## Jalon 13 — Test RAG précoce (US4, P4) — juge de paix

**Goal** : prouver, sur l'échantillon annoté, que le format tient sa
promesse : les bons chunks remontent en tête sur des questions
cross-domaines ; sinon, corriger le format **avant** toute généralisation.

**Independent Test** : vectoriser l'échantillon, poser les 2 questions,
constater les attendus dans le top-k, documenter le constat.

**Échantillon figé (5 fichiers — protocole du constat, 2026-08-28)** :
`app/domains/users/services.py`, `app/domains/organizations/services.py`,
`app/core/database.py` (minimum FR-015 — intégralement annoté depuis
l'extension du périmètre `[RAG]`), **plus** `app/domains/users/router.py`
(4ᵉ fichier, requis pour que Q2 puisse remonter un chunk d'endpoint
montrant `Depends(get_db)`) **et** `app/domains/users/models.py`
(5ᵉ fichier, amendement du protocole : le format `[MODEL]` doit être
éprouvé, et le bloc users est le chunk d'arêtes le plus riche).

**Questions de contrôle figées** :

- **Q1** — « que se passe-t-il quand on supprime un utilisateur ? » —
  attendus : chunk `delete_user` + métadonnées des arêtes concernées
  (organisations, commentaires, assignation) (FR-017).
- **Q2** — « comment une requête HTTP obtient-elle une session de base de
  données ? » (arbitrage acté : teste le **graphe d'appels et les tiers**,
  pas les arêtes FK déjà couvertes par Q1) — attendus : chunk `get_db` avec
  son en-tête `CRITICAL_CORE` et `called_by` multi-domaines, plus un chunk
  d'endpoint de `users/router.py` montrant `Depends(get_db)`.

- [ ] **T075** [J13] Dépendances dev : `fastembed` + `numpy` au groupe dev
      Poetry ; vérifier la disponibilité des wheels sous Python 3.14 local ;
      si absentes, acter le repli R5 (venv 3.12 jetable dédié au seul
      `rag_probe.py`) et le consigner dans le constat T080.
- [ ] **T076** [J13] **Chunker** dans `scripts/rag_probe.py` (Standard V3,
      hors corpus) : découpage par marqueurs — un chunk = un bloc `[RAG]` +
      sa fonction (ancrages du format normatif) ; boilerplate d'imports
      exclu via `[CODE_START]` (FR-016) ; robustesse aux fichiers sans
      en-têtes `[RAG]` par fonction maintenue (`models.py`/`schemas.py`,
      edge case de la spec — `core/database.py` n'en est plus le cas
      d'usage, l'échantillon étant intégralement annoté) ; échantillon figé
      ci-dessus.
- [ ] **T077** [P] [J13] Tests du chunker seul (pur, sans embedding) dans
      `tests/unit/test_rag_probe.py` : bornes des chunks, exclusion du
      boilerplate, un chunk par fonction annotée, cas du fichier non annoté.
- [ ] **T078** [J13] **Vectorisation et classement** dans `rag_probe.py` :
      embeddings fastembed (`paraphrase-multilingual-MiniLM-L12-v2`), index
      = matrice numpy en mémoire, similarité cosinus, **top-k = 5** brut
      (R5) — pas de base vectorielle, pas de framework RAG.
- [ ] **T079** [J13] Exécution **Q1** : classement top-5 complet relevé,
      présence/rang des attendus (`delete_user`, métadonnées d'arêtes)
      constatés.
- [ ] **T080** [J13] Exécution **Q2** : classement top-5 complet relevé,
      présence/rang des attendus (`get_db` CRITICAL_CORE multi-domaines,
      endpoint avec `Depends(get_db)`) constatés.
- [ ] **T081** [J13] **CONSTAT DOCUMENTÉ** —
      `specs/002-phase3-metadata/jalon13-constat.md` : protocole (échantillon,
      modèle, k), résultat top-k **question par question** (classement
      intégral, attendus présents/absents avec leur rang), verdict motivé
      (FR-018, SC-005). **C'est le livrable du jalon, pas un à-côté.** En cas
      d'échec : cause formulée dans le constat, correction du format
      d'annotation (retour jalons 10–11), régénération `rag-annotate`,
      re-test — **avant toute généralisation** ; l'échec est un résultat
      documenté, pas une exception.
- [ ] **T082** [J13] **GATE 13** : `make rag-check` vert ; pytest intégral ;
      MyPy `--strict` ; Ruff `check` + `format --check` ; constat T081
      versionné.
- [ ] **T083** [J13] **COMMIT de gate du jalon 13** — **clôture de la
      phase 3** ; mise à jour du bloc de validation phase 3 dans CLAUDE.md
      (amendement de gouvernance en commit distinct si rédigé séparément).

---

## Dependencies & Execution Order

### Entre jalons

Ordre **strict et bloquant** : J10 → J11 → J12 → J13. Un jalon n'ouvre que
lorsque le précédent est clos par son commit de gate (T063, T070, T074,
T083). Aucune parallélisation inter-jalons.

### À l'intérieur des jalons

- **J10** : T056 (module partagé) précède T058 (générateur) et T060/T061 ;
  T057 et T059 sont [P] entre eux dès que leur cible existe ; T061 → T062 →
  T063 strictement séquentiels.
- **J11** : T064 → T065 ; T066 [P] dès T065 ; T067 → T068 → T069 → T070.
- **J12** : T071 → T072 → T073 → T074.
- **J13** : T075 → T076 → T078 (T077 [P] dès T076) ; T078 → T079/T080
  (les deux questions peuvent s'exécuter à la suite dans la même session) →
  T081 → T082 → T083.

### Boucle d'échec du jalon 13

T081 en échec ré-ouvre J10/J11 (correction du format), puis `rag-annotate`,
puis re-exécution T079/T080 et nouveau constat T081 — la généralisation
(phase 5) reste fermée tant que le verdict n'est pas positif.

---

## Notes

- Chaque gate (T062, T069, T073, T082) se prouve **après annotation** — les
  en-têtes sont des commentaires, mais c'est vérifié, jamais supposé (R10).
- Les commits de gate (T063, T070, T074, T083) sont des tâches à part
  entière : un jalon n'est clos qu'une fois commité (FR-019).
- Piège heredoc en vigueur pendant tout le développement des scripts :
  motif `["\']` proscrit, forme `(?:'|")` obligatoire (R9).
- Aucune tâche ne modifie fonctionnellement `app/` ni ne généralise
  l'indexation — hors périmètre (FR-006, spec Assumptions).
