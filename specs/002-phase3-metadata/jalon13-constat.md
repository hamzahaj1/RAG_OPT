# Jalon 13 — Constat du test RAG précoce

**Branch**: `002-phase3-metadata` | **Protocole consigné le**: 2026-08-28
| **Statut**: relevé R1 exécuté le 2026-08-28 — **ÉCHEC partiel sur les
deux questions ; exécution arrêtée avant toute correction** (protocole
§5), hypothèse de cause en attente de validation

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

### Pistes de correction possibles (NON exécutées — en attente d'arbitrage)

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
