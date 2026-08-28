# Jalon 13 — Constat du test RAG précoce

**Branch**: `002-phase3-metadata` | **Protocole consigné le**: 2026-08-28
| **Statut**: protocole figé, exécution non commencée

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

## Inventaire des chunks

*(à remplir à l'exécution — T076)*

## Relevés

*(à remplir à l'exécution — T079/T080)*

## Verdict

*(à remplir — T081)*
