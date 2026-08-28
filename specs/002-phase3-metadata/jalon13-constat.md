# Jalon 13 — Constat du test RAG précoce

**Branch**: `002-phase3-metadata` | **Protocole consigné le**: 2026-08-28
| **Statut**: relevé R3 exécuté le 2026-08-28 sur piste 4 instruite
(décision de gouvernance — modèle `intfloat/multilingual-e5-large` +
préfixes `query:`/`passage:`, seule variable modifiée) — **Q2 en SUCCÈS
intégral (première question résolue du jalon), Q1 en ÉCHEC persistant
sur le seul critère B** (`User [MODEL]` rang 6, à 0.0018 du seuil) ;
exécution arrêtée (protocole §5), suite actée : migration linguistique
du corpus puis relevé R4 (CLAUDE.md §4 ter)

> **Le constat est le livrable.** Un échec proprement documenté vaut
> mieux qu'un succès arrangé — c'est toute la raison d'être du jalon
> (CLAUDE.md §8 : point de contrôle décisif du projet).

## Protocole (figé avant exécution — commit de gouvernance)

### 1. Variables gelées pendant tout le jalon

| Variable | Valeur figée |
|---|---|
| Échantillon (5 fichiers) | `app/domains/users/services.py`, `app/domains/organizations/services.py`, `app/core/database.py`, `app/domains/users/router.py`, `app/domains/users/models.py` |
| Question Q1 (verbatim) | « que se passe-t-il quand on supprime un utilisateur ? » |
| Question Q2 (verbatim) | « comment une requête HTTP obtient-elle une session de base de données ? » |
| k | 5 |
| Modèle d'embedding | consigné à l'exécution de T075 : nom exact + version de fastembed (épinglés ci-dessous, puis inamovibles) |
| Chunking | un chunk = un bloc `# [RAG]` … `# [/RAG]` + sa fonction (jusqu'au chunk suivant ou à la fin du fichier) ; un bloc `# [MODEL]`/`# [SCHEMA]` = un chunk à lui seul ; boilerplate d'imports et en-tête de fichier exclus via `[CODE_START]` (FR-016) |
| Identifiants de chunks | `<module>.<fonction> [RAG]` ; `<module>.<Entité> [MODEL]` ; `<module> [SCHEMA]` |
| Corpus | l'échantillon ci-dessus, tel qu'annoté par `rag-annotate` au commit du gate 12 — aucune retouche manuelle |

**Seule dérogation admise** : un relevé *diagnostic* en anglais si un
attendu manque — daté et étiqueté `[DIAGNOSTIC]`, il ne remplace jamais
le verdict français.

### 2. Inventaire d'abord

Le constat commence par l'**inventaire intégral des chunks**
(identifiants + comptage par fichier) avant tout relevé de question.

### 3. Constat brut avant interprétation

Pour chaque question : le **top-5 intégral** est consigné tel quel —
rang, score de similarité cosinus à **4 décimales** (égalités
signalées), identifiant de chunk — *avant* toute interprétation. Le
verdict vient après, jamais mêlé au relevé.

### 4. Critères de succès binaires (figés)

| Question | Succès si et seulement si |
|---|---|
| Q1 | le chunk `users.services.delete_user [RAG]` est dans le **top-3** **ET** le chunk `users.models.User [MODEL]` est dans le **top-5** |
| Q2 | le chunk `core.database.get_db [RAG]` est dans le **top-3** **ET** un chunk d'endpoint de `users.router` portant `Depends(get_db)` est dans le **top-5** |

### 5. Échec = résultat ; boucle de correction gouvernée

Si un attendu manque : le relevé reste tel quel, l'hypothèse de cause
est nommée dans le constat, et **l'exécution s'arrête immédiatement** —
la boucle de correction (retour J10/J11 → régénération `rag-annotate` →
nouveau relevé **daté et ajouté**, jamais de réécriture d'un relevé)
ne s'engage que sur validation explicite de l'hypothèse par le
mainteneur.

---

## Modèle épinglé (T075, 2026-08-28)

- **Modèle** : `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **fastembed** : `0.8.0` (numpy `2.5.2`, Python local 3.14 — wheels
  présents, le repli venv 3.12 de R5 n'a pas été nécessaire ;
  dépendances marquées `python >= 3.12` dans le groupe dev, plancher
  projet 3.11 intact)
- **Note consignée** : fastembed ≥ 0.6 applique le *mean pooling* à ce
  modèle (avertissement à l'exécution : « now uses mean pooling instead
  of CLS embedding ») — comportement épinglé avec la version.

**Amendement R3 (2026-08-28, décision de gouvernance — piste 4
instruite)** : la variable gelée « modèle d'embedding » est changée —
c'est la seule modification depuis R2.

- **Modèle** : `intfloat/multilingual-e5-large` (fenêtre 512 tokens ;
  artefact ONNX fastembed `qdrant/multilingual-e5-large-onnx`),
  fastembed `0.8.0` inchangé.
- **Protocole d'usage e5** : préfixes `passage: ` sur chaque chunk et
  `query: ` sur chaque question, appliqués **côté sonde** à la
  vectorisation — le corpus sur disque est strictement inchangé
  (constantes `PASSAGE_PREFIX`/`QUERY_PREFIX` de `scripts/rag_probe.py` ;
  vérifié : la classe fastembed de ce modèle n'applique aucun préfixe
  automatique, pas de double préfixe).
- Questions françaises verbatim, k=5, échantillon et chunking inchangés.

## Inventaire des chunks (T076 — avant tout relevé)

**19 chunks** : `users.services` 6 × [RAG] (`_hash_password`,
`create_user`, `delete_user`, `get_user`, `list_users`, `update_user`) ;
`organizations.services` 5 × [RAG] (`create_organization`,
`delete_organization`, `get_organization`, `list_organizations`,
`update_organization`) ; `core.database` 2 × [RAG] (`get_db`,
`init_db_engine`) ; `users.router` 5 × [RAG] (`create_user`,
`delete_user`, `get_user`, `list_users`, `update_user`) ;
`users.models` 1 × [MODEL] (`User`).

Comptage verrouillé par `tests/unit/test_rag_probe.py`
(`test_sample_inventory_matches_frozen_protocol`).

## Relevés

### Relevé R1 — 2026-08-28 (`python -m scripts.rag_probe`)

**Q1 — « que se passe-t-il quand on supprime un utilisateur ? »**

| Rang | Score | Chunk |
|---|---|---|
| 1 | 0.5651 | `users.services.delete_user [RAG]` |
| 2 | 0.5208 | `users.router.delete_user [RAG]` |
| 3 | 0.4601 | `users.services.get_user [RAG]` |
| 4 | 0.4409 | `users.services.update_user [RAG]` |
| 5 | 0.4062 | `users.router.update_user [RAG]` |

Aucune égalité à 4 décimales.
Critère A (`delete_user [RAG]` top-3) : **VRAI** (rang 1).
Critère B (`users.models.User [MODEL]` top-5) : **FAUX** (absent du top-5).

**Q2 — « comment une requête HTTP obtient-elle une session de base de
données ? »**

| Rang | Score | Chunk |
|---|---|---|
| 1 | 0.4193 | `users.models.User [MODEL]` |
| 2 | 0.4089 | `users.router.create_user [RAG]` |
| 3 | 0.4073 | `users.router.get_user [RAG]` |
| 4 | 0.3808 | `users.services.get_user [RAG]` |
| 5 | 0.3695 | `users.services.create_user [RAG]` |

Aucune égalité à 4 décimales.
Critère A (`core.database.get_db [RAG]` top-3) : **FAUX** (absent du
top-5).
Critère B (endpoint `Depends(get_db)` top-5) : **VRAI** (rangs 2 et 3).

## Verdict

**ÉCHEC sur les deux questions** (Q1 : critère B ; Q2 : critère A) —
conformément au protocole §5, **l'exécution s'est arrêtée là** : aucune
correction engagée, la boucle J10/J11 attend la validation de
l'hypothèse de cause.

### Hypothèse de cause (à valider avant toute correction)

Le format d'annotation place l'en-tête `[RAG]` **en tête de chunk**, et
le modèle épinglé a une fenêtre courte (~128 tokens pour
`paraphrase-multilingual-MiniLM-L12-v2`) : le chunk est **tronqué avant
sa sémantique** quand l'en-tête est volumineux.

- `core.database.get_db [RAG]` : 1 692 caractères ; le bloc `called_by`
  (25 noms qualifiés) occupe le début du chunk et la docstring
  (« Fournit une session DB par requête HTTP ») ne commence qu'au
  caractère **1 039** — hors fenêtre. L'embedding représente une liste
  d'identifiants, pas la sémantique de session → Q2-A échoue.
- Contre-épreuve interne : `users.services.delete_user [RAG]`
  (1 749 caractères mais en-tête court — `called_by` à 1 entrée) a sa
  docstring dans la fenêtre → rang 1 sur Q1.
- `users.models.User [MODEL]` (261 caractères, dans la fenêtre) est un
  bloc de **métadonnées pures sans phrase en langage naturel** : faible
  proximité avec une question française → Q1-B échoue. Son rang 1
  anormal sur Q2 est cohérent avec des représentations dominées par des
  identifiants (« users », « user ») plutôt que par le sens.

### [DIAGNOSTIC] 2026-08-28 — measurement notes (English, per protocol §1)

Chunk sizes (chars / words / est. tokens): `get_db [RAG]` 1692 / 160 /
~224+; `delete_user [RAG]` 1749 / 223 / ~312 (docstring within window —
header short); `users.User [MODEL]` 261 / 35 / ~49 (fits window, no
natural-language content); `users.router.create_user [RAG]` 595 / 75 /
~105. The `get_db` docstring starts at char 1039 of 1692 — past any
~128-token window. Qualified dotted identifiers tokenize expensively,
so real token counts exceed the word-based estimates.

### Relevé R2 — 2026-08-28 (`python -m scripts.rag_probe`, après boucles J10+J11)

**Corrections appliquées avant R2** (pistes 2 et 3 validées par le
mainteneur ; piste 1 rejetée — masque le format ; piste 4 en réserve de
gouvernance) : en-têtes `[RAG]` réordonnés (signature, tier, weight,
reads, mutates, puis calls/called_by) et listes d'appels plafonnées à 5
avec synthèse déterministe (commit `5bb6d0d`) — le chunk `get_db` passe
de 1 692 à **998 caractères**, docstring au caractère **345** ; synthèse
française générée en tête de `[MODEL]`/`[SCHEMA]` (commit `48a2885`).
**Aucune variable de sonde modifiée** : mêmes questions verbatim, même
modèle, même k, même échantillon — seul le corpus régénéré change.
Inventaire inchangé : 19 chunks, mêmes identifiants.

**Q1 — « que se passe-t-il quand on supprime un utilisateur ? »**

| Rang | Score | Chunk |
|---|---|---|
| 1 | 0.5592 | `users.services.delete_user [RAG]` |
| 2 | 0.5174 | `users.router.delete_user [RAG]` |
| 3 | 0.4523 | `users.services.get_user [RAG]` |
| 4 | 0.4388 | `users.services.update_user [RAG]` |
| 5 | 0.4163 | `users.router.update_user [RAG]` |

Aucune égalité à 4 décimales.
Critère A : **VRAI** (rang 1). Critère B : **FAUX** —
`users.models.User [MODEL]` au rang **9**/19 (0.3622).

**Q2 — « comment une requête HTTP obtient-elle une session de base de
données ? »**

| Rang | Score | Chunk |
|---|---|---|
| 1 | 0.3962 | `users.router.create_user [RAG]` |
| 2 | 0.3929 | `users.router.get_user [RAG]` |
| 3 | 0.3779 | `users.services.get_user [RAG]` |
| 4 | 0.3645 | `users.services.create_user [RAG]` |
| 5 | 0.3628 | `users.router.list_users [RAG]` |

Aucune égalité à 4 décimales.
Critère A : **FAUX** — `core.database.get_db [RAG]` au rang **6**/19
(0.3552, à **0.0076** du rang 5). Critère B : **VRAI** (rangs 1, 2, 5).

**Verdict R2 : ÉCHEC persistant** (Q1-B, Q2-A) — mêmes critères qu'en
R1. Progression objective des deux attendus :

- `get_db` sur Q2 : hors top-5 (R1) → **rang 6**, à 0.0076 du seuil —
  l'hypothèse de troncature était juste mais la correction ne suffit pas
  à franchir le seuil avec ce modèle ;
- l'anomalie R1 (`users.models.User [MODEL]` rang 1 sur Q2) a
  **disparu** (rang 11) — la synthèse française a corrigé la
  représentation dominée par les identifiants ;
- `users.models.User [MODEL]` sur Q1 : hors top-5 (R1) → rang 9.

### [DIAGNOSTIC] 2026-08-28 — R2 measurement notes (English, per protocol §1)

Full-ranking positions (19 chunks): Q1 → `User [MODEL]` 9th (0.3622),
`get_db` 17th; Q2 → `get_db` 6th (0.3552, gap to 5th = 0.0076),
`User [MODEL]` 11th, `init_db_engine` 19th. The `get_db` chunk now
contains 13 occurrences of "session" within 998 chars, docstring at
char 345 — yet scores only 0.3552 against a near-verbatim French
question. Residual causes point at the **pinned model's capacity**, not
the format: mean pooling over ~250 mostly-code tokens dilutes the
4-line docstring; minor lexical gap ("session DB" vs « base de
données »). Both failing targets improved monotonically across
R1 → R2 under frozen probe variables.

### Relevé R3 — 2026-08-28 (`python -m scripts.rag_probe`, piste 4 instruite)

**Correction appliquée avant R3** (décision de gouvernance du
2026-08-28) : modèle `intfloat/multilingual-e5-large` avec préfixes
`query:`/`passage:` appliqués côté sonde (amendement consigné à la
section « Modèle épinglé » ci-dessus). **Une seule variable modifiée
depuis R2** : le corpus est celui du commit `48a2885` (inchangé depuis
R2), questions françaises verbatim, même k, même échantillon.
Inventaire inchangé : 19 chunks, mêmes identifiants.

**Q1 — « que se passe-t-il quand on supprime un utilisateur ? »**

| Rang | Score | Chunk |
|---|---|---|
| 1 | 0.8458 | `users.router.delete_user [RAG]` |
| 2 | 0.8296 | `users.services.delete_user [RAG]` |
| 3 | 0.8168 | `users.services.get_user [RAG]` |
| 4 | 0.8164 | `users.services.update_user [RAG]` |
| 5 | 0.8081 | `organizations.services.delete_organization [RAG]` |

Aucune égalité à 4 décimales dans le top-5.
Critère A : **VRAI** (rang 2). Critère B : **FAUX** —
`users.models.User [MODEL]` au rang **6**/19 (0.8063, à **0.0018** du
rang 5, en égalité à 4 décimales avec le rang 7).

**Q2 — « comment une requête HTTP obtient-elle une session de base de
données ? »**

| Rang | Score | Chunk |
|---|---|---|
| 1 | 0.8654 | `core.database.get_db [RAG]` |
| 2 | 0.8312 | `users.router.get_user [RAG]` |
| 3 | 0.8309 | `users.services.get_user [RAG]` |
| 4 | 0.8285 | `organizations.services.get_organization [RAG]` |
| 5 | 0.8257 | `users.router.list_users [RAG]` |

Aucune égalité à 4 décimales.
Critère A : **VRAI** — `core.database.get_db [RAG]` au rang **1**, avec
la plus forte marge du jalon (+0.0342 sur le rang 2). Critère B :
**VRAI** (rangs 2 et 5).

**Verdict R3 : Q2 SUCCÈS intégral — première question résolue du
jalon ; Q1 ÉCHEC persistant sur le seul critère B.** Trajectoire des
deux attendus sous variables de corpus gelées :

- `get_db` sur Q2 : hors top-5 (R1) → rang 6 (R2) → **rang 1** (R3) —
  l'hypothèse R1 (troncature de fenêtre) est **confirmée en creux** :
  la fenêtre de 512 tokens absorbe le chunk entier, la sémantique de
  session domine ;
- `users.models.User [MODEL]` sur Q1 : hors top-5 (R1) → rang 9 (R2) →
  **rang 6** (R3), à 0.0018 du seuil — progression monotone, mais un
  bloc de métadonnées à synthèse française d'une ligne reste dominé par
  cinq chunks de code porteurs de docstrings et de `[STEP]` complets.

### [DIAGNOSTIC] 2026-08-28 — R3 measurement notes (English, per protocol §1)

Full-ranking positions (19 chunks): Q1 → `User [MODEL]` 6th (0.8063,
gap to 5th = 0.0018, tied at 4 decimals with `users.services.create_user`
7th); Q2 → `get_db` **1st** (0.8654, margin +0.0342 over 2nd),
`User [MODEL]` 19th, `init_db_engine` 16th. Score distribution is much
tighter under e5-large (Q1 spread 0.7557–0.8458 vs 0.4062–0.5651 under
MiniLM R1): asymmetric `query:`/`passage:` prefixing lifts all cosine
scores; only relative order is meaningful. The remaining Q1-B failure is
no longer a window problem (the `[MODEL]` block, 375 chars, fits any
window): the one-line French synthesis plus pure-identifier metadata
competes against full code chunks whose docstrings state deletion
policies verbatim in French. Language migration of the corpus (CLAUDE.md
§4 ter) is the next governed variable — R4 will measure it.

### Suite (gouvernance)

La boucle de format (pistes 2–3) a produit un progrès mesurable mais
insuffisant sous le modèle épinglé. Conformément à l'arbitrage du
2026-08-28, **la piste 4 — modèle à fenêtre longue
(`intfloat/multilingual-e5-large`, 512 tokens) — est la réserve à
instruire comme décision de gouvernance** (changement d'une variable
gelée du protocole). Aucune autre correction n'est engagée sans
validation.

**Addendum post-R3 (2026-08-28)** : la piste 4 a été instruite et
exécutée (relevé R3 ci-dessus) — Q2 résolue, Q1-B persiste à 0.0018 du
seuil. Conformément à CLAUDE.md §4 ter (politique de langue, séquencement
acté), la suite est la **migration linguistique du corpus indexable vers
l'anglais** en trois lots gatés (générateurs, `app/`, `CONTRACTS.md`),
puis l'amendement des questions du jalon (la langue des questions suit
celle du corpus) et le **relevé R4** — arrêt après R4, verdict quel
qu'il soit. R1–R3 restent intacts au constat ; la comparaison R3 → R4
documentera l'effet de langue pour la phase 5.

### Pistes de correction possibles (identifiées à R1 — NON exécutées alors, statut mis à jour)

1. **Composition du texte vectorisé** (correction côté sonde, format
   sur disque inchangé) : embarquer docstring + signature + champs
   sémantiques (`tier`, `reads`, `mutates`) en tête, replier
   `calls`/`called_by` en queue ou en résumé (« 25 appelants,
   5 domaines »).
2. **Format d'annotation** (boucle J10/J11) : plafonner `called_by`
   dans l'en-tête (top-N + comptage), le graphe intégral restant dans
   `TOPOLOGY.yaml`.
3. **Enrichissement `[MODEL]`** (boucle J11) : une ligne de synthèse en
   langage naturel dérivée des politiques (« la suppression d'un
   utilisateur est bloquée par ses organisations et commentaires,
   l'assignation est détachée ») — générée, jamais manuelle.
4. **Modèle à fenêtre longue** (`intfloat/multilingual-e5-large`,
   512 tokens) — **changement d'une variable gelée** : décision de
   gouvernance, pas un réglage.
