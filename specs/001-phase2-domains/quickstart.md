# Quickstart — Validation Phase 2

**Feature**: `001-phase2-domains` — guide de validation de bout en bout.
Détails des champs : [data-model.md](data-model.md) · endpoints : [contracts/api.md](contracts/api.md).

## Prérequis

```bash
make up                 # PostgreSQL 16 + Adminer (podman compose)
poetry install          # installe aussi bcrypt, pydantic[email], httpx (jalon 4+)
```

## Gate de clôture d'un jalon (identique pour les jalons 4 → 9)

À exécuter dans cet ordre, tout doit être vert avant d'ouvrir le jalon suivant :

```bash
make db-revision m="<domaine>_domain"   # autogenerate + ruff sur alembic/versions/
make db-migrate                          # la migration s'applique sans erreur
poetry run pytest                        # unit + integration, PostgreSQL réel
poetry run mypy app alembic tests        # strict, zéro erreur
poetry run ruff check app alembic tests && poetry run ruff format --check app alembic tests
```

## Validation fonctionnelle par jalon

Application lancée : `poetry run python -m app.main` (ou uvicorn). Swagger : `http://localhost:8000/docs`.

**Jalon 4 — users** :

```bash
curl -s -X POST localhost:8000/api/v1/users -H 'Content-Type: application/json' \
  -d '{"email":"alice@example.com","full_name":"Alice","role":"admin","password":"s3cret-pw"}'
# → 201, corps sans aucun champ mot de passe
curl -s localhost:8000/api/v1/users                    # → 200, liste paginée
curl -s -X POST ... (même email)                       # → 409
curl -s localhost:8000/api/v1/users/999                # → 404
```

**Jalon 5 — organizations** : créer une org avec `owner_id` valide (201),
avec `owner_id=999` (404 « User 999 not found »), puis `DELETE` de
l'utilisateur propriétaire → 409.

**Jalon 6 — projects** : créer un projet dans l'org (201), org inexistante
(404), doublon de nom dans la même org (409), puis `DELETE` de l'org → 409.

**Jalon 7 — tasks** : créer une tâche non assignée (201), l'assigner via
PATCH (200), `status` invalide (422), `DELETE` de l'assigné → 204 et la
tâche restitue `assignee_id: null`.

**Jalon 8 — comments** : commenter une tâche (201), lister
`GET /api/v1/comments?task_id=N` (200), auteur inexistant (404),
`DELETE` de la tâche → 204 et ses commentaires ont disparu ;
`DELETE` d'un utilisateur auteur → 409.

**Jalon 9 — seed** :

```bash
make db-seed && make db-seed    # deux exécutions consécutives
```

Vérifier dans Adminer (`http://localhost:8080`) : mêmes comptes de lignes
après chaque exécution, zéro doublon, les six arêtes FK représentées,
les trois statuts et trois priorités présents.

## Résultat attendu en fin de phase

- 25 endpoints actifs (5 domaines × 5), conformes à [contracts/api.md](contracts/api.md).
- Suite de tests complète verte contre PostgreSQL réel.
- 6 migrations Alembic empilées sur la baseline `f2476b2dee09`.
- `make db-seed` idempotent.
- MyPy strict et Ruff verts sur `app/`, `alembic/`, `tests/`.
