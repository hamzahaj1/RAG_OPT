# Feature Specification: Phase 2 — Domaines métier

**Feature Branch**: `001-phase2-domains`

**Created**: 2026-08-27

**Status**: Draft

**Input**: User description: "Phase 2 du plan d'exécution de CLAUDE.md (section 8) : les domaines. Six jalons en ordre strict — jalon 4 : domaine users ; jalon 5 : organizations (FK owner_id → users.id) ; jalon 6 : projects (FK organization_id → organizations.id) ; jalon 7 : tasks (FK project_id → projects.id, assignee_id → users.id) ; jalon 8 : comments (FK task_id → tasks.id, author_id → users.id) ; jalon 9 : seed idempotent. Chaque domaine : 4 fichiers + tests unit et integration, Standard Alpha-Scope V3 intégral, validation par jalon (migration, tests verts, MyPy strict, Ruff)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gestion des utilisateurs (Priority: P1)

Un administrateur de la plateforme peut créer, consulter, lister, modifier et
supprimer des comptes utilisateurs. Chaque utilisateur possède une identité
unique (email), un nom affichable et un rôle qui déterminera plus tard ses
permissions. Ce domaine est le socle : toutes les relations de propriété,
d'assignation et de paternité du système pointent vers lui.

**Why this priority**: Aucun autre domaine ne peut exister sans lui —
`organizations`, `tasks` et `comments` référencent tous des utilisateurs. C'est
aussi le premier passage complet du cycle « domaine + tests + migration +
validation », qui calibre le patron reproduit par les quatre domaines suivants.

**Independent Test**: Peut être testé intégralement seul — cycle CRUD complet
sur les utilisateurs via l'API, sans qu'aucun autre domaine n'existe.

**Acceptance Scenarios**:

1. **Given** aucune donnée, **When** on crée un utilisateur avec un email, un nom et un rôle valides, **Then** l'utilisateur est persisté et restitué avec un identifiant et ses horodatages.
2. **Given** un utilisateur existant avec l'email X, **When** on crée un second utilisateur avec l'email X, **Then** la création est refusée avec une erreur de conflit explicite.
3. **Given** un utilisateur existant, **When** on le consulte, le modifie puis le supprime, **Then** chaque opération répond avec l'état attendu et la consultation après suppression signale l'absence.
4. **Given** un identifiant inexistant, **When** on consulte, modifie ou supprime cet utilisateur, **Then** le système répond « introuvable » sans effet de bord.

---

### User Story 2 - Gestion des organisations (Priority: P2)

Un utilisateur peut créer une organisation dont il est propriétaire. Les
organisations regroupent les projets et matérialisent la notion de
« qui possède quoi » sur la plateforme.

**Why this priority**: Première relation inter-domaines du système
(`owner_id → users.id`). Elle valide que le patron d'intégrité référentielle
fonctionne avant de le répliquer sur les domaines plus riches.

**Independent Test**: Testable dès que `users` existe — cycle CRUD complet sur
les organisations, avec vérification qu'un propriétaire inexistant est refusé.

**Acceptance Scenarios**:

1. **Given** un utilisateur existant, **When** on crée une organisation avec cet utilisateur comme propriétaire, **Then** l'organisation est persistée et rattachée à lui.
2. **Given** aucun utilisateur avec l'identifiant Y, **When** on crée une organisation avec Y comme propriétaire, **Then** la création est refusée avec une erreur explicite désignant la référence invalide.
3. **Given** une organisation existante, **When** on la liste, la consulte, la modifie et la supprime, **Then** chaque opération répond avec l'état attendu.

---

### User Story 3 - Gestion des projets (Priority: P3)

Un membre d'une organisation peut créer des projets rattachés à celle-ci.
Le projet est le domaine central de la plateforme : c'est autour de lui que
s'organisent les tâches.

**Why this priority**: Dépend de `organizations` (FK `organization_id`) et
conditionne `tasks`. Ordre imposé par la chaîne de dépendances.

**Independent Test**: Testable dès que `organizations` existe — cycle CRUD
complet sur les projets, avec refus d'une organisation inexistante.

**Acceptance Scenarios**:

1. **Given** une organisation existante, **When** on crée un projet rattaché à elle, **Then** le projet est persisté et restitué avec son rattachement.
2. **Given** une organisation inexistante, **When** on tente d'y créer un projet, **Then** la création est refusée avec une erreur explicite.
3. **Given** plusieurs projets dans une organisation, **When** on liste les projets, **Then** la liste est paginée et restitue les projets attendus.

---

### User Story 4 - Gestion des tâches (Priority: P4)

Un utilisateur peut créer des tâches dans un projet, leur donner un statut et
une priorité, et les assigner (ou non) à un utilisateur. C'est le premier
domaine à double référence inter-domaines.

**Why this priority**: Dépend de `projects` et `users`, et conditionne
`comments`. C'est aussi le domaine qui introduit les ensembles fermés de
valeurs (statuts, priorités) et la référence optionnelle (assigné).

**Independent Test**: Testable dès que `projects` existe — cycle CRUD complet,
transitions de statut, assignation et désassignation.

**Acceptance Scenarios**:

1. **Given** un projet existant, **When** on crée une tâche avec un statut et une priorité valides, sans assigné, **Then** la tâche est persistée, non assignée.
2. **Given** une tâche existante et un utilisateur existant, **When** on assigne la tâche à cet utilisateur, **Then** la tâche restitue son assigné.
3. **Given** une tâche, **When** on lui applique un statut ou une priorité hors de l'ensemble autorisé, **Then** la modification est refusée avec une erreur de validation.
4. **Given** un projet inexistant ou un assigné inexistant, **When** on crée une tâche les référençant, **Then** la création est refusée avec une erreur explicite.

---

### User Story 5 - Gestion des commentaires (Priority: P5)

Un utilisateur peut commenter une tâche. Les commentaires portent la relation
la plus imbriquée du système (commentaire → tâche → projet → organisation →
utilisateur), celle qui servira de cas d'épreuve au pipeline RAG pour les
questions cross-domaines.

**Why this priority**: Dernier maillon de la chaîne de dépendances (FK
`task_id` et `author_id`). Ferme le graphe relationnel décrit dans CLAUDE.md §3.

**Independent Test**: Testable dès que `tasks` existe — cycle CRUD complet sur
les commentaires d'une tâche, avec refus de tâche ou d'auteur inexistants.

**Acceptance Scenarios**:

1. **Given** une tâche et un utilisateur existants, **When** l'utilisateur commente la tâche, **Then** le commentaire est persisté avec sa tâche et son auteur.
2. **Given** une tâche inexistante ou un auteur inexistant, **When** on crée un commentaire les référençant, **Then** la création est refusée avec une erreur explicite.
3. **Given** une tâche avec plusieurs commentaires, **When** on liste les commentaires de cette tâche, **Then** la liste restitue les commentaires de cette tâche uniquement.
4. **Given** une tâche avec des commentaires, **When** la tâche est supprimée, **Then** ses commentaires disparaissent avec elle.

---

### User Story 6 - Jeu de données de démonstration idempotent (Priority: P6)

Un développeur (ou le pipeline RAG en phase 5) peut peupler la base avec un jeu
de données réaliste couvrant les cinq domaines et toutes leurs relations, d'une
seule commande, autant de fois qu'il le veut, sans jamais créer de doublons ni
d'état divergent.

**Why this priority**: Dépend des cinq domaines. C'est l'outillage qui rendra
les tests du « tireur » (phase 5) reproductibles.

**Independent Test**: Exécuter la commande de peuplement deux fois de suite sur
une base vide — l'état final est identique après chaque exécution.

**Acceptance Scenarios**:

1. **Given** une base vide, **When** on lance le peuplement, **Then** la base contient des utilisateurs, organisations, projets, tâches et commentaires reliés entre eux et couvrant chaque relation du graphe.
2. **Given** une base déjà peuplée par ce même peuplement, **When** on relance la commande, **Then** aucun doublon n'est créé et l'état final est identique à celui de la première exécution.

---

### Edge Cases

- Création d'une entité référençant un parent inexistant (propriétaire, organisation, projet, tâche, assigné, auteur) → refus explicite, aucune écriture partielle.
- Suppression d'une entité encore référencée : un utilisateur propriétaire d'organisations ou auteur de commentaires ne peut pas être supprimé silencieusement en laissant des références orphelines — le comportement (blocage, cascade ou détachement) est défini entité par entité dans les exigences et vérifié par les tests.
- Doublon sur une contrainte d'unicité (email utilisateur) → erreur de conflit, pas d'écrasement.
- Modification partielle : seuls les champs fournis changent, les autres restent intacts.
- Consultation, modification ou suppression d'un identifiant inexistant → réponse « introuvable » cohérente sur les cinq domaines.
- Valeur hors de l'ensemble fermé (rôle, statut, priorité) → erreur de validation, jamais de valeur libre persistée.
- Liste vide → réponse valide avec collection vide, pas une erreur.
- Bornes de pagination invalides ou extrêmes → réponse bornée et prévisible.
- Peuplement relancé après une exécution partielle interrompue → convergence vers le même état final.

## Requirements *(mandatory)*

### Functional Requirements

**Transversal — les cinq domaines**

- **FR-001**: Chaque domaine (`users`, `organizations`, `projects`, `tasks`, `comments`) DOIT exposer le cycle complet : créer, consulter par identifiant, lister, modifier partiellement, supprimer.
- **FR-002**: Toute référence vers une entité d'un autre domaine DOIT être vérifiée à l'écriture ; une référence inexistante DOIT produire une erreur explicite désignant la référence fautive, sans écriture partielle.
- **FR-003**: Toute opération sur un identifiant inexistant DOIT produire une réponse « introuvable » cohérente d'un domaine à l'autre.
- **FR-004**: Les listes DOIVENT être paginées avec des bornes par défaut et maximales définies, identiques sur les cinq domaines.
- **FR-005**: Chaque entité DOIT porter un identifiant stable et ses horodatages de création et de dernière modification.
- **FR-006**: Un domaine ne DOIT connaître les autres que par ses références explicites (FK) — aucun couplage de logique inter-domaines.

**Users (jalon 4)**

- **FR-007**: Un utilisateur DOIT posséder un email unique sur toute la plateforme ; un doublon DOIT être refusé avec une erreur de conflit.
- **FR-008**: Le rôle d'un utilisateur DOIT appartenir à un ensemble fermé (au minimum : administrateur, membre).
- **FR-009**: Le secret d'authentification d'un utilisateur DOIT être stocké sous forme irréversible et ne DOIT jamais apparaître dans aucune réponse de l'API.
- **FR-010**: Un utilisateur encore propriétaire d'une organisation ne DOIT PAS pouvoir être supprimé ; la suppression DOIT être refusée avec une erreur explicite.

**Organizations (jalon 5)**

- **FR-011**: Une organisation DOIT avoir exactement un propriétaire, qui est un utilisateur existant (`owner_id → users.id`).
- **FR-012**: La suppression d'une organisation contenant encore des projets DOIT être refusée avec une erreur explicite.

**Projects (jalon 6)**

- **FR-013**: Un projet DOIT être rattaché à exactement une organisation existante (`organization_id → organizations.id`).
- **FR-014**: La suppression d'un projet DOIT entraîner la disparition de ses tâches (et, par ricochet, de leurs commentaires).

**Tasks (jalon 7)**

- **FR-015**: Une tâche DOIT être rattachée à exactement un projet existant (`project_id → projects.id`).
- **FR-016**: Une tâche PEUT être assignée à un utilisateur existant (`assignee_id → users.id`) ; l'assignation est optionnelle et révocable.
- **FR-017**: Le statut d'une tâche DOIT appartenir à un ensemble fermé (à faire, en cours, terminé) ; sa priorité aussi (basse, moyenne, haute).
- **FR-018**: La suppression d'un utilisateur assigné à des tâches DOIT désassigner ces tâches sans les supprimer.

**Comments (jalon 8)**

- **FR-019**: Un commentaire DOIT être rattaché à exactement une tâche existante (`task_id → tasks.id`) et un auteur existant (`author_id → users.id`).
- **FR-020**: La suppression d'une tâche DOIT entraîner la disparition de ses commentaires.
- **FR-021**: Les commentaires DOIVENT être listables par tâche.

**Seed (jalon 9)**

- **FR-022**: Une commande unique DOIT peupler la base avec un jeu de données couvrant les cinq domaines et chacune des six relations du graphe (CLAUDE.md §3).
- **FR-023**: Le peuplement DOIT être idempotent : relancé N fois, l'état final de la base est identique — aucun doublon, aucune divergence.

**Validation par jalon**

- **FR-024**: Chaque jalon DOIT être livré avec ses tests unitaires et d'intégration, ces derniers exécutés contre une base réelle dédiée aux tests, jamais un substitut en mémoire.
- **FR-025**: Chaque jalon DOIT inclure sa migration de schéma générée par l'outillage du projet, et passer l'intégralité des vérifications de qualité (typage strict, lint, formatage) avant l'ouverture du jalon suivant.

### Key Entities

- **User**: personne identifiée sur la plateforme — email unique, nom affichable, rôle (ensemble fermé), secret d'authentification stocké de façon irréversible. Référencé par les organisations (propriétaire), les tâches (assigné) et les commentaires (auteur).
- **Organization**: regroupement possédant les projets — nom, propriétaire (→ User).
- **Project**: domaine central — nom, description, organisation de rattachement (→ Organization). Contient les tâches.
- **Task**: unité de travail — titre, description, statut et priorité (ensembles fermés), projet de rattachement (→ Project), assigné optionnel (→ User). Contient les commentaires.
- **Comment**: message imbriqué — contenu, tâche de rattachement (→ Task), auteur (→ User).

**Graphe relationnel** (toutes les relations inter-domaines du système) :

```
organizations.owner_id   → users.id          (obligatoire, suppression bloquée)
projects.organization_id → organizations.id  (obligatoire, suppression bloquée)
tasks.project_id         → projects.id       (obligatoire, cascade)
tasks.assignee_id        → users.id          (optionnel, détachement)
comments.task_id         → tasks.id          (obligatoire, cascade)
comments.author_id       → users.id          (obligatoire, suppression bloquée)
```

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100 % des opérations du cycle de vie (créer, consulter, lister, modifier, supprimer) sont disponibles et fonctionnelles pour chacun des cinq domaines.
- **SC-002**: Chaque scénario d'acceptation des six user stories est couvert par au moins un test automatisé, et l'intégralité de la suite passe au vert.
- **SC-003**: Aucune opération de l'API ne permet de créer une référence orpheline ou une valeur hors des ensembles fermés — vérifié par les tests des cas limites.
- **SC-004**: Le peuplement de démonstration exécuté deux fois de suite produit un état de base strictement identique (zéro doublon).
- **SC-005**: 100 % des vérifications automatiques de qualité du projet passent sans erreur ni avertissement à la clôture de chaque jalon.
- **SC-006**: Les six jalons sont validés dans l'ordre strict 4 → 9, chacun avant l'ouverture du suivant.

## Assumptions

- **Authentification hors périmètre** : le domaine `users` stocke le rôle et le secret irréversible, mais aucun endpoint de connexion (login/token) n'est livré en phase 2 — le plan d'exécution (CLAUDE.md §8) n'en prévoit pas avant les phases suivantes. Seul le socle de données est posé.
- **Ensembles fermés par défaut** : rôles = {admin, member} ; statuts de tâche = {todo, in_progress, done} ; priorités = {low, medium, high}. Valeurs standard du domaine Jira/Linear simplifié, ajustables sans impact structurel.
- **Politique de suppression** : blocage quand l'entité est encore propriétaire ou auteure (users ← organizations, users ← comments, organizations ← projects), cascade le long de l'axe de contenance (projects → tasks → comments), détachement pour l'assignation optionnelle (tasks.assignee_id). C'est le comportement le moins destructeur cohérent avec le graphe.
- **Pagination** : paramètres décalage/limite avec limite par défaut de 50 et maximale de 100, uniformes sur les cinq domaines.
- **Fondation acquise** : la phase 1 est validée (noyau applicatif, base de données, migrations opérationnelles) ; la phase 2 s'appuie dessus sans la modifier.
- **Gouvernance héritée (contrainte, pas choix de conception)** : la forme du code livré est régie intégralement par CLAUDE.md — Standard Alpha-Scope V3 (§6) sur les services et routeurs, 4 fichiers par domaine (§5), sessions de base de données via l'unique dépendance prévue, tests d'intégration contre la base réelle, migrations via l'outillage du Makefile (§4 bis), sans en-têtes `[RAG]` (générés en phase 3). Le détail d'application relève du plan d'implémentation, pas de cette spécification.
