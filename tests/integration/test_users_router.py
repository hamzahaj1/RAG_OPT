# [FILE] — tests/integration/test_users_router.py
"""Tests d'intégration du domaine users — parcours API contre PostgreSQL réel.

Une fonction de test par scénario d'acceptation ou cas limite du contrat :
create 201 (sans champ mot de passe), doublon email 409, get 200/404,
liste et pagination (défauts, bornes, 422), PATCH partiel 200/404/409,
PATCH du rôle en round-trip API → DB → API, delete 204 puis 404,
delete id inconnu 404.
"""

# ─── IMPORTS ───
from typing import Any

from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.users.models import User

# ──────────────

# [CODE_START]

USER_PAYLOAD: dict[str, str] = {
    "email": "alice@example.com",
    "full_name": "Alice",
    "password": "s3cret-pw",
    "role": "admin",
}


async def _create_user(client: AsyncClient, email: str) -> dict[str, Any]:
    """Crée un utilisateur via l'API et retourne le corps de la réponse 201.

    Invariant : un échec de création fait échouer immédiatement le test
    appelant (assertion sur le statut) — jamais d'état partiel silencieux.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    body: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Poster le payload de référence avec l'email fourni → utilisateur persisté
    response = await client.post("/api/v1/users", json={**USER_PAYLOAD, "email": email})
    assert response.status_code == 201
    body = response.json()
    return body


async def test_create_user_duplicate_email_returns_409(client: AsyncClient) -> None:
    """Un second utilisateur sur le même email est refusé en conflit (FR-007)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Occuper l'email → première création persistée
    await _create_user(client, "dup@example.com")

    # [STEP 2] Re-soumettre le même email → 409, détail explicite
    response = await client.post("/api/v1/users", json={**USER_PAYLOAD, "email": "dup@example.com"})
    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"


async def test_create_user_returns_201_without_password(client: AsyncClient) -> None:
    """La création répond 201 avec id et horodatages, sans aucun champ mot de passe."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    body: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Créer l'utilisateur de référence → 201 attendu
    response = await client.post("/api/v1/users", json=USER_PAYLOAD)
    assert response.status_code == 201

    # [STEP 2] Inspecter le corps → contrat UserRead respecté, aucun champ sensible
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["full_name"] == "Alice"
    assert body["role"] == "admin"
    assert isinstance(body["id"], int)
    assert "created_at" in body
    assert "updated_at" in body
    assert "password" not in body
    assert "hashed_password" not in body


async def test_delete_user_removes_user(client: AsyncClient) -> None:
    """La suppression répond 204 sans corps, puis la consultation répond 404."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    created: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Créer puis supprimer l'utilisateur → 204, corps vide
    created = await _create_user(client, "temp@example.com")
    response = await client.delete(f"/api/v1/users/{created['id']}")
    assert response.status_code == 204
    assert response.content == b""

    # [STEP 2] Consulter l'id supprimé → 404, la suppression est effective
    response = await client.get(f"/api/v1/users/{created['id']}")
    assert response.status_code == 404


async def test_delete_user_unknown_id_returns_404(client: AsyncClient) -> None:
    """Supprimer un id inconnu répond 404 sans effet de bord (FR-003)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Supprimer un id jamais attribué → 404, détail nommant l'entité
    response = await client.delete("/api/v1/users/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "User 999 not found"


async def test_get_user_returns_200(client: AsyncClient) -> None:
    """La consultation restitue exactement l'état renvoyé à la création."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    created: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Créer puis consulter l'utilisateur → 200, corps identique au créé
    created = await _create_user(client, "carol@example.com")
    response = await client.get(f"/api/v1/users/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


async def test_get_user_unknown_id_returns_404(client: AsyncClient) -> None:
    """Consulter un id inconnu répond 404 avec un détail explicite (FR-003)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Consulter un id jamais attribué → 404, détail nommant l'entité
    response = await client.get("/api/v1/users/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "User 999 not found"


async def test_list_users_applies_pagination_bounds(client: AsyncClient) -> None:
    """``limit`` et ``offset`` découpent la liste triée par id croissant."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    index: int
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Créer trois utilisateurs → ids 1, 2, 3 (identités remises à zéro)
    for index in range(3):
        await _create_user(client, f"user{index}@example.com")

    # [STEP 2] Demander la page limit=1 offset=1 → uniquement le deuxième utilisateur
    response = await client.get("/api/v1/users", params={"limit": 1, "offset": 1})
    assert response.status_code == 200
    assert [user["email"] for user in response.json()] == ["user1@example.com"]


async def test_list_users_rejects_out_of_bounds_pagination(client: AsyncClient) -> None:
    """Des bornes hors contrat (limit 0 ou 101, offset négatif) répondent 422."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    params: dict[str, int]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Soumettre chaque borne invalide → 422 systématique, aucune lecture
    for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}):
        response = await client.get("/api/v1/users", params=params)
        assert response.status_code == 422


async def test_list_users_returns_default_page(client: AsyncClient) -> None:
    """Sans paramètres : liste vide valide, puis page par défaut triée par id."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Lister une base vide → 200 et collection vide, pas une erreur
    response = await client.get("/api/v1/users")
    assert response.status_code == 200
    assert response.json() == []

    # [STEP 2] Créer deux utilisateurs et relister → défauts appliqués, tri par id
    await _create_user(client, "bob@example.com")
    await _create_user(client, "carla@example.com")
    response = await client.get("/api/v1/users")
    assert response.status_code == 200
    assert [user["email"] for user in response.json()] == [
        "bob@example.com",
        "carla@example.com",
    ]


async def test_update_user_duplicate_email_returns_409(client: AsyncClient) -> None:
    """Un PATCH vers un email déjà enregistré est refusé en conflit (FR-007)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    created: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Occuper un email et créer la cible du PATCH → deux utilisateurs distincts
    await _create_user(client, "taken@example.com")
    created = await _create_user(client, "free@example.com")

    # [STEP 2] Patcher la cible vers l'email occupé → 409, détail explicite
    response = await client.patch(
        f"/api/v1/users/{created['id']}", json={"email": "taken@example.com"}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"


async def test_update_user_partial_patch_updates_only_given_fields(client: AsyncClient) -> None:
    """Seuls les champs présents dans le corps changent (sémantique exclude_unset)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    body: dict[str, Any]
    created: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Créer l'utilisateur cible → état initial connu
    created = await _create_user(client, "dave@example.com")

    # [STEP 2] Patcher uniquement full_name → 200, les autres champs intacts
    response = await client.patch(
        f"/api/v1/users/{created['id']}", json={"full_name": "Dave Renamed"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Dave Renamed"
    assert body["email"] == "dave@example.com"
    assert body["role"] == created["role"]
    assert body["id"] == created["id"]


async def test_update_user_role_round_trips_api_db_api(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Le rôle patché traverse API → DB → API sans altération de valeur (FR-008).

    Chemin sensible : ``update_user`` applique ``model_dump`` sans
    ``mode="json"`` — le rôle transite en ``UserRole`` et doit être persisté
    comme sa valeur chaîne exacte, puis relu identique par l'API.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    created: dict[str, Any]
    response: Response
    stored_role: str | None
    # ─────────────────────────────────────────

    # [STEP 1] Créer un utilisateur member → état initial distinct de la cible du PATCH
    response = await client.post(
        "/api/v1/users", json={**USER_PAYLOAD, "email": "erin@example.com", "role": "member"}
    )
    assert response.status_code == 201
    created = response.json()
    assert created["role"] == "member"

    # [STEP 2] Patcher le rôle vers admin → 200, la réponse reflète le changement
    response = await client.patch(f"/api/v1/users/{created['id']}", json={"role": "admin"})
    assert response.status_code == 200
    assert response.json()["role"] == "admin"

    # [STEP 3] Lire la colonne en DB → la valeur persistée est la chaîne exacte
    stored_role = await db_session.scalar(select(User.role).where(User.id == created["id"]))
    assert stored_role == "admin"

    # [STEP 4] Relire via l'API → le round-trip complet restitue le rôle patché
    response = await client.get(f"/api/v1/users/{created['id']}")
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


async def test_update_user_unknown_id_returns_404(client: AsyncClient) -> None:
    """Patcher un id inconnu répond 404 sans effet de bord (FR-003)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Patcher un id jamais attribué → 404, détail nommant l'entité
    response = await client.patch("/api/v1/users/999", json={"full_name": "Nobody"})
    assert response.status_code == 404
    assert response.json()["detail"] == "User 999 not found"
