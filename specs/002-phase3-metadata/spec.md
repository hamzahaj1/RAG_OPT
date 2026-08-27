# Feature Specification: Phase 3 — Métadonnées

**Feature Branch**: `002-phase3-metadata`

**Created**: 2026-08-27

**Status**: Draft

**Input**: User description: "Phase 3 du plan d'exécution de CLAUDE.md (section 8) : les métadonnées. Quatre jalons en ordre strict — jalon 10 : generate_topology_headers.py (analyse AST, résolution des imports, graphe d'appels, weight/tier, insertion des en-têtes [RAG] sur services.py et router.py) ; jalon 11 : generate_structural_metadata.py ([MODEL] sur models.py, [SCHEMA] sur schemas.py, TOPOLOGY.yaml déterministe) ; jalon 12 : CONTRACTS.md (6 arêtes FK cross-domaines, politique de suppression, double couche, invariants) ; jalon 13 : test RAG précoce (vectorisation d'un échantillon, questions cross-domaines, bons chunks dans le top-k). Idempotence stricte des scripts, gate qualité vert après annotation, corpus RAG = app/ exclusivement, un commit par gate."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - En-têtes de topologie générés par analyse du code (Priority: P1)

Le mainteneur du corpus (humain ou pipeline) peut, d'une seule commande,
faire analyser l'intégralité du code applicatif et insérer sur chaque
fonction des services et des routeurs un en-tête `[RAG]` machine-readable :
signature, poids dans le graphe d'appels, niveau (`tier`), fonctions
appelées et appelantes, tables lues et mutées. Ces en-têtes ne sont
**jamais** écrits à la main — ils sont dérivés du code réel, donc toujours
exacts.

**Why this priority**: C'est la matière première du pipeline RAG : sans
topologie exacte, aucun découpage sémantique fiable. C'est aussi le jalon
qui fige la sémantique `weight`/`tier` pour tout le reste du projet.

**Independent Test**: Exécuter la génération sur le code de la phase 2 —
chaque fonction de chaque `services.py` et `router.py` des cinq domaines
porte un en-tête complet, et aucun import du corpus n'est resté non résolu.

**Acceptance Scenarios**:

1. **Given** le code applicatif de la phase 2 sans en-têtes, **When** on lance la génération de topologie, **Then** toutes les fonctions des services et routeurs des cinq domaines portent un en-tête `[RAG]` complet (signature, weight, tier, calls, called_by, reads, mutates).
2. **Given** le graphe d'appels résolu, **When** on inspecte les en-têtes, **Then** `weight` égale le nombre d'appels entrants plus sortants de la fonction dans le graphe, et `tier` respecte la classification figée (LEAF / CORE / CRITICAL_CORE).
3. **Given** un import ou un alias de module dans le corpus, **When** l'analyse s'exécute, **Then** l'import est résolu vers sa cible réelle — zéro import non résolu, et tout échec de résolution est signalé explicitement, jamais ignoré en silence.
4. **Given** un code déjà annoté, **When** on relance la génération sans changement du code, **Then** le résultat est strictement identique (aucune accumulation, aucun décalage).

---

### User Story 2 - Métadonnées structurelles et carte du graphe (Priority: P2)

Le mainteneur peut générer les annotations structurelles des modèles
(`[MODEL]`) et des schémas (`[SCHEMA]`), ainsi qu'une carte complète du
graphe d'appels du corpus, sérialisée à la racine du projet
(`TOPOLOGY.yaml`) de façon déterministe — la même entrée produit
octet pour octet la même sortie.

**Why this priority**: Complète la couverture d'annotation (les quatre
fichiers de chaque domaine) et produit l'artefact global que le pipeline
de la phase 5 consommera comme index structurel. Dépend de l'analyse du
jalon 10.

**Independent Test**: Générer deux fois de suite — `TOPOLOGY.yaml` existe,
décrit le graphe complet, et les deux générations sont identiques.

**Acceptance Scenarios**:

1. **Given** les modèles et schémas des cinq domaines, **When** on lance la génération structurelle, **Then** chaque `models.py` porte son annotation `[MODEL]` et chaque `schemas.py` son annotation `[SCHEMA]`.
2. **Given** le corpus analysé, **When** la génération produit `TOPOLOGY.yaml`, **Then** le fichier décrit le graphe d'appels complet avec des clés triées et un ordre stable.
3. **Given** un `TOPOLOGY.yaml` déjà produit, **When** on régénère sans changement du code, **Then** le nouveau fichier est identique au précédent.

---

### User Story 3 - Contrats inter-domaines documentés (Priority: P3)

Tout lecteur du projet (développeur, revue, ou LLM du pipeline) dispose à
la racine d'un document unique, `CONTRACTS.md`, qui documente chacune des
six arêtes FK cross-domaines : sa politique de suppression, sa
vérification en double couche (refus applicatif explicite + garantie
en base), et les invariants métier qu'elle porte.

**Why this priority**: C'est la documentation de référence des questions
cross-domaines — précisément celles que le test RAG du jalon 13 posera.
Elle se rédige à partir des migrations et des docstrings existantes, qui
font foi ; aucune réinvention.

**Independent Test**: Vérifier que les six arêtes du graphe (CLAUDE.md §3)
sont documentées et que chaque affirmation concorde avec le modèle de
données de la phase 2.

**Acceptance Scenarios**:

1. **Given** le graphe relationnel de la phase 2, **When** on lit `CONTRACTS.md`, **Then** les six arêtes y figurent, chacune avec sa politique de suppression (blocage, cascade ou détachement), sa double couche de vérification et ses invariants métier.
2. **Given** le modèle de données de la phase 2 (`data-model.md`, migrations), **When** on confronte `CONTRACTS.md` à ces sources, **Then** aucune contradiction — le document reflète l'existant, il ne le réinvente pas.

---

### User Story 4 - Test RAG précoce : le juge de paix (Priority: P4)

L'architecte du pipeline peut vérifier, sur un échantillon réduit de
fichiers annotés, que le format d'annotation tient sa promesse : découpé
par les marqueurs du standard puis vectorisé, le corpus répond correctement
à des questions cross-domaines — les bons fragments remontent en tête du
classement. Si ce n'est pas le cas, le format est corrigé **avant** toute
généralisation.

**Why this priority**: C'est le point de contrôle décisif de tout le
projet (CLAUDE.md §8, jalon 13) : il est infiniment moins coûteux de
corriger le format d'annotation sur trois fichiers que sur soixante-dix.
Tout le reste de la phase 3 n'existe que pour être validé ici.

**Independent Test**: Vectoriser l'échantillon annoté, poser les questions
de contrôle, constater la présence des fragments attendus dans le top-k,
documenter le constat.

**Acceptance Scenarios**:

1. **Given** un échantillon d'au moins trois fichiers annotés (au minimum les services de `users` et `organizations` et le noyau base de données), **When** on le découpe par les marqueurs du standard, **Then** chaque fragment est une fonction avec son en-tête `[RAG]`, et le boilerplate d'imports n'apparaît dans aucun fragment.
2. **Given** le corpus vectorisé, **When** on pose la question « que se passe-t-il quand on supprime un utilisateur ? », **Then** les fragments remontés incluent la fonction de suppression d'utilisateur et les métadonnées des arêtes concernées (organisations, commentaires, assignation).
3. **Given** le corpus vectorisé, **When** on pose une seconde question cross-domaine, **Then** les fragments attendus figurent dans le top-k du classement.
4. **Given** un échec de remontée (mauvais fragments en tête), **When** le constat est posé, **Then** le format d'annotation est corrigé et le test rejoué avant toute généralisation — l'échec est un résultat documenté, pas une exception.

---

### Edge Cases

- Import non résolu ou alias de module ambigu pendant l'analyse → échec explicite et nommé, jamais un en-tête silencieusement incomplet.
- Ré-exécution de la génération sur un code déjà annoté → remplacement strict du bloc délimité, jamais d'accumulation ; deux exécutions successives laissent l'arbre de travail sans aucune modification.
- Code modifié entre deux générations → les en-têtes reflètent le nouveau graphe ; un en-tête périmé ne survit pas à la régénération.
- Fonction jamais appelée dans le corpus hors de son routeur → classée `LEAF`, poids reflétant ses seuls appels sortants.
- Fonction référencée par de multiples domaines (noyau) → classée `CRITICAL_CORE`, jamais diluée dans un niveau inférieur.
- Les annotations générées ne modifient aucun comportement : la suite de tests, le typage strict et le lint passent à l'identique après annotation — vérifié à chaque gate, pas supposé.
- Développement des scripts via heredoc bash : le motif d'échappement des guillemets connu pour se corrompre est proscrit au profit de la forme sûre consignée dans la charte (§7).
- L'échantillon du jalon 13 contient un fichier du noyau (`core/`) non annoté par les scripts des jalons 10–11 (hors services/routeurs/modèles/schémas) → le découpage doit rester correct sur ses marqueurs de base.

## Requirements *(mandatory)*

### Functional Requirements

**Transversal — les deux scripts de génération**

- **FR-001**: Les annotations (`[RAG]`, `[MODEL]`, `[SCHEMA]`) ne DOIVENT jamais être écrites ni retouchées à la main : elles sont produites exclusivement par les scripts de génération, par analyse du code réel.
- **FR-002**: L'insertion des annotations DOIT être un remplacement délimité par marqueurs — jamais une accumulation. Deux exécutions successives sur un code inchangé DOIVENT produire un arbre de travail strictement identique (diff vide).
- **FR-003**: Une commande unique DOIT exécuter les deux générations (annotation complète), et une commande de contrôle DOIT échouer si l'annotation n'est pas à jour (annotation + vérification de diff vide, sur le modèle du contrôle de dérive des migrations).
- **FR-004**: L'intégralité des vérifications de qualité du projet (tests, typage strict, lint, formatage) DOIT rester verte après annotation — prouvé à chaque gate de la phase, jamais supposé.
- **FR-005**: Les scripts de génération DOIVENT suivre le Standard Alpha-Scope V3 intégral (la charte s'applique à tous les fichiers), tout en restant HORS du corpus RAG indexable — le corpus est le code applicatif (`app/`) exclusivement.
- **FR-006**: La phase 3 ne DOIT modifier aucun comportement du code applicatif : les annotations sont des commentaires ; aucune signature, aucune logique, aucun contrat d'API ne change.

**Topologie (jalon 10)**

- **FR-007**: L'analyse DOIT résoudre la totalité des imports et alias de modules du corpus ; zéro import non résolu, et tout échec de résolution DOIT être signalé explicitement.
- **FR-008**: L'analyse DOIT construire le graphe d'appels complet du corpus et calculer pour chaque fonction : `weight` = nombre d'appels entrants + nombre d'appels sortants dans le graphe résolu.
- **FR-009**: Chaque fonction DOIT être classée sur une échelle fermée : `LEAF` = aucun appel entrant hors de son routeur ; `CORE` = référencée par au moins un service ou le peuplement ; `CRITICAL_CORE` = les points d'accès du noyau (`get_db`, `settings`) et toute fonction référencée par trois domaines ou plus.
- **FR-010**: Chaque fonction de chaque `services.py` et `router.py` des cinq domaines DOIT recevoir un en-tête `[RAG]` complet : signature, weight, tier, calls, called_by, reads (tables lues), mutates (tables mutées).

**Structure (jalon 11)**

- **FR-011**: Chaque `models.py` DOIT recevoir son annotation `[MODEL]` et chaque `schemas.py` son annotation `[SCHEMA]`.
- **FR-012**: La génération DOIT produire `TOPOLOGY.yaml` à la racine : graphe d'appels complet, sérialisation déterministe (clés triées, ordre stable) — deux générations sur un code inchangé produisent des fichiers identiques.

**Contrats (jalon 12)**

- **FR-013**: `CONTRACTS.md` à la racine DOIT documenter chacune des six arêtes FK cross-domaines : politique de suppression (blocage / cascade / détachement), vérification double couche (refus applicatif + garantie en base), et invariants métier portés par l'arête.
- **FR-014**: `CONTRACTS.md` DOIT être établi à partir des sources de vérité existantes (migrations, docstrings, modèle de données de la phase 2) et rester cohérent avec elles — aucune règle réinventée.

**Test RAG précoce (jalon 13)**

- **FR-015**: Un échantillon d'au moins trois fichiers annotés DOIT être vectorisé, incluant au minimum les services de `users`, les services de `organizations` et le noyau base de données (`core/database.py`).
- **FR-016**: Le découpage DOIT suivre les marqueurs du standard : un fragment = une fonction avec son en-tête `[RAG]` ; le boilerplate d'imports est exclu des fragments via le marqueur de début de code.
- **FR-017**: Au moins deux questions cross-domaines DOIVENT être posées au corpus vectorisé, dont « que se passe-t-il quand on supprime un utilisateur ? » — les fragments remontés DOIVENT inclure la fonction de suppression d'utilisateur et les métadonnées des arêtes concernées.
- **FR-018**: Le constat du test (réussite ou échec, fragments remontés, classement) DOIT être documenté ; en cas d'échec, le format d'annotation DOIT être corrigé et le test rejoué avant toute généralisation de l'indexation.

**Validation par jalon**

- **FR-019**: Chaque jalon (10, 11, 12, 13) DOIT être clos par un gate complet vert (tests, typage strict, lint, formatage, contrôle d'idempotence de l'annotation) suivi d'un commit sur la branche de la phase — un jalon n'est clos qu'une fois commité ; les amendements de gouvernance font l'objet de commits distincts.

### Key Entities

- **En-tête `[RAG]`**: bloc de métadonnées machine-readable porté par chaque fonction des services et routeurs — signature, weight, tier, calls, called_by, reads, mutates. Produit par analyse, jamais manuel.
- **Graphe d'appels**: ensemble des fonctions du corpus et de leurs relations d'appel résolues (imports et alias compris). Source unique de `weight`, `tier`, `calls`, `called_by`.
- **`TOPOLOGY.yaml`**: sérialisation déterministe du graphe d'appels à la racine du projet — l'index structurel global du corpus.
- **`CONTRACTS.md`**: documentation de référence des six arêtes FK cross-domaines et de leurs politiques, dérivée des sources de vérité de la phase 2.
- **Fragment (chunk)**: unité d'indexation du corpus — une fonction et son en-tête `[RAG]`, découpée par les marqueurs du standard, sans boilerplate d'imports.
- **Corpus RAG**: le code applicatif (`app/`) exclusivement — les scripts de génération, specs, tests et migrations en sont exclus.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100 % des fonctions des `services.py` et `router.py` des cinq domaines portent un en-tête `[RAG]` complet et exact ; zéro import non résolu dans l'analyse.
- **SC-002**: Deux exécutions successives de l'annotation complète sur un code inchangé produisent un diff strictement vide ; `TOPOLOGY.yaml` est identique entre deux générations.
- **SC-003**: La suite de tests, le typage strict et le lint passent au vert après annotation, à chacun des quatre gates de la phase.
- **SC-004**: Les six arêtes FK cross-domaines sont documentées dans `CONTRACTS.md` sans contradiction avec le modèle de données de la phase 2.
- **SC-005**: Sur le corpus échantillon vectorisé, chacune des questions cross-domaines de contrôle fait remonter les fragments attendus dans le top-k, et le constat est documenté ; en cas d'échec, la correction du format précède toute généralisation.
- **SC-006**: Les quatre jalons sont validés dans l'ordre strict 10 → 13, chacun clos par son commit de gate avant l'ouverture du suivant.

## Assumptions

- **Sémantique `weight`/`tier` imposée (décision figée avant la première ligne de code)** : `weight` = appels entrants + appels sortants dans le graphe résolu ; `LEAF` = 0 appel entrant hors routeur ; `CORE` = référencé par au moins un service ou le peuplement ; `CRITICAL_CORE` = `get_db`, `settings`, et toute fonction référencée par 3+ domaines. Toute évolution de cette sémantique est une décision de gouvernance, pas un choix d'implémentation.
- **Noms d'outillage imposés (décision figée, à reprendre dans research.md)** : la commande unique d'annotation et la commande de contrôle de FR-003 sont les cibles Makefile `rag-annotate` (exécute les deux scripts de génération) et `rag-check` (annotation puis vérification de diff vide via `git diff --exit-code`, sur le modèle du contrôle de dérive Alembic).
- **Frontière du corpus** : le corpus RAG indexable est `app/` exclusivement ; `scripts/`, `.specify/`, `specs/`, `tests/` et `alembic/` en sont exclus — les scripts de `scripts/` suivent néanmoins le Standard V3 (charte : « tous les fichiers »). Cette frontière est consignée dans CLAUDE.md.
- **Choix d'outillage du jalon 13 délégué au plan** : le modèle de vectorisation et le magasin de vecteurs de l'échantillon sont choisis en phase de planification (research.md) — la spécification n'impose que le protocole (découpage par marqueurs, questions de contrôle, top-k, constat documenté).
- **Piège d'outillage consigné (charte §7)** : dans un heredoc bash, le motif regex `["\']` se corrompt — la forme `(?:'|")` est obligatoire pendant tout le développement des scripts.
- **Base acquise** : la phase 2 est close (tag `phase-2-complete`) ; la phase 3 s'appuie sur son code et sa gouvernance sans modifier aucun comportement applicatif.
- **Hors périmètre** : toute généralisation de l'indexation au corpus complet (jalon 18, phase 5), tout frontend (phase 4), toute modification fonctionnelle de `app/`.
