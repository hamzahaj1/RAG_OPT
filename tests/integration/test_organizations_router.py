# [FILE] — tests/integration/test_organizations_router.py
"""Tests d'intégration du domaine organizations — parcours API contre PostgreSQL réel.

Une fonction de test par scénario d'acceptation ou cas limite du contrat :
create 201, doublon de nom 409, propriétaire inexistant 404, get 200/404,
liste et pagination (défauts, bornes, 422), PATCH partiel 200/404/409,
delete 204 puis 404, delete id inconnu 404, suppression du propriétaire
d'une organisation refusée en 409 (première FK du projet).
"""

# ─── IMPORTS ───
from typing import Any

from httpx import AsyncClient, Response

# ──────────────

# [CODE_START]

OWNER_PAYLOAD: dict[str, str] = {
    "email": "owner@example.com",
    "full_name": "Olivia Owner",
    "password": "s3cret-pw",
    "role": "member",
}


async def _create_organization(client: AsyncClient, name: str, owner_id: int) -> dict[str, Any]:
    """Crée une organisation via l'API et retourne le corps de la réponse 201.

    Invariant : un échec de création fait échouer immédiatement le test
    appelant (assertion sur le statut) — jamais d'état partiel silencieux.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    body: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Poster le nom et le propriétaire fournis → organisation persistée
    response = await client.post("/api/v1/organizations", json={"name": name, "owner_id": owner_id})
    assert response.status_code == 201
    body = response.json()
    return body


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
    response = await client.post("/api/v1/users", json={**OWNER_PAYLOAD, "email": email})
    assert response.status_code == 201
    body = response.json()
    return body


async def test_create_organization_duplicate_name_returns_409(client: AsyncClient) -> None:
    """Une seconde organisation sur le même nom est refusée en conflit (FR-012)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    owner: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Occuper le nom → première création persistée
    owner = await _create_user(client, "dup-org@example.com")
    await _create_organization(client, "Acme Corp", owner["id"])

    # [STEP 2] Re-soumettre le même nom → 409, détail explicite
    response = await client.post(
        "/api/v1/organizations", json={"name": "Acme Corp", "owner_id": owner["id"]}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Organization name already taken"


async def test_create_organization_returns_201_with_owner(client: AsyncClient) -> None:
    """La création répond 201 avec id, propriétaire et horodatages (contrat Read)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    body: dict[str, Any]
    owner: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Créer le propriétaire puis l'organisation → 201 attendu
    owner = await _create_user(client, "acme-owner@example.com")
    response = await client.post(
        "/api/v1/organizations", json={"name": "Acme Corp", "owner_id": owner["id"]}
    )
    assert response.status_code == 201

    # [STEP 2] Inspecter le corps → contrat OrganizationRead respecté
    body = response.json()
    assert body["name"] == "Acme Corp"
    assert body["owner_id"] == owner["id"]
    assert isinstance(body["id"], int)
    assert "created_at" in body
    assert "updated_at" in body


async def test_create_organization_unknown_owner_returns_404(client: AsyncClient) -> None:
    """Un propriétaire inexistant est refusé en 404 avant toute écriture (FR-011)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Poster une organisation vers un owner jamais attribué → 404, détail nommé
    response = await client.post(
        "/api/v1/organizations", json={"name": "Ghost Corp", "owner_id": 999}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User 999 not found"


async def test_delete_organization_removes_organization(client: AsyncClient) -> None:
    """La suppression répond 204 sans corps, puis la consultation répond 404."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    created: dict[str, Any]
    owner: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Créer puis supprimer l'organisation → 204, corps vide
    owner = await _create_user(client, "temp-org@example.com")
    created = await _create_organization(client, "Temp Corp", owner["id"])
    response = await client.delete(f"/api/v1/organizations/{created['id']}")
    assert response.status_code == 204
    assert response.content == b""

    # [STEP 2] Consulter l'id supprimé → 404, la suppression est effective
    response = await client.get(f"/api/v1/organizations/{created['id']}")
    assert response.status_code == 404


async def test_delete_organization_unknown_id_returns_404(client: AsyncClient) -> None:
    """Supprimer un id inconnu répond 404 sans effet de bord (FR-003)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Supprimer un id jamais attribué → 404, détail nommant l'entité
    response = await client.delete("/api/v1/organizations/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Organization 999 not found"


async def test_delete_owner_of_organization_returns_409(client: AsyncClient) -> None:
    """Supprimer le propriétaire d'une organisation est refusé en conflit (D2).

    Double couche : le 409 vient du SELECT applicatif de ``delete_user`` ;
    la FK ``RESTRICT`` en DB reste le backstop si ce contrôle disparaît.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    owner: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Créer un propriétaire et son organisation → FK owner_id posée
    owner = await _create_user(client, "held-owner@example.com")
    await _create_organization(client, "Held Corp", owner["id"])

    # [STEP 2] Tenter de supprimer le propriétaire → 409, l'utilisateur subsiste
    response = await client.delete(f"/api/v1/users/{owner['id']}")
    assert response.status_code == 409
    assert response.json()["detail"] == f"User {owner['id']} still owns organizations"

    # [STEP 3] Consulter le propriétaire → 200, aucune suppression partielle
    response = await client.get(f"/api/v1/users/{owner['id']}")
    assert response.status_code == 200


async def test_get_organization_returns_200(client: AsyncClient) -> None:
    """La consultation restitue exactement l'état renvoyé à la création."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    created: dict[str, Any]
    owner: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Créer puis consulter l'organisation → 200, corps identique au créé
    owner = await _create_user(client, "carol-org@example.com")
    created = await _create_organization(client, "Carol Corp", owner["id"])
    response = await client.get(f"/api/v1/organizations/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


async def test_get_organization_unknown_id_returns_404(client: AsyncClient) -> None:
    """Consulter un id inconnu répond 404 avec un détail explicite (FR-003)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Consulter un id jamais attribué → 404, détail nommant l'entité
    response = await client.get("/api/v1/organizations/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Organization 999 not found"


async def test_list_organizations_applies_pagination_bounds(client: AsyncClient) -> None:
    """``limit`` et ``offset`` découpent la liste triée par id croissant."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    index: int
    owner: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Créer trois organisations → ids 1, 2, 3 (identités remises à zéro)
    owner = await _create_user(client, "pager@example.com")
    for index in range(3):
        await _create_organization(client, f"Org {index}", owner["id"])

    # [STEP 2] Demander la page limit=1 offset=1 → uniquement la deuxième organisation
    response = await client.get("/api/v1/organizations", params={"limit": 1, "offset": 1})
    assert response.status_code == 200
    assert [organization["name"] for organization in response.json()] == ["Org 1"]


async def test_list_organizations_rejects_out_of_bounds_pagination(client: AsyncClient) -> None:
    """Des bornes hors contrat (limit 0 ou 101, offset négatif) répondent 422."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    params: dict[str, int]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Soumettre chaque borne invalide → 422 systématique, aucune lecture
    for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}):
        response = await client.get("/api/v1/organizations", params=params)
        assert response.status_code == 422


async def test_list_organizations_returns_default_page(client: AsyncClient) -> None:
    """Sans paramètres : liste vide valide, puis page par défaut triée par id."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    owner: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Lister une base vide → 200 et collection vide, pas une erreur
    response = await client.get("/api/v1/organizations")
    assert response.status_code == 200
    assert response.json() == []

    # [STEP 2] Créer deux organisations et relister → défauts appliqués, tri par id
    owner = await _create_user(client, "lister@example.com")
    await _create_organization(client, "Alpha Corp", owner["id"])
    await _create_organization(client, "Beta Corp", owner["id"])
    response = await client.get("/api/v1/organizations")
    assert response.status_code == 200
    assert [organization["name"] for organization in response.json()] == [
        "Alpha Corp",
        "Beta Corp",
    ]


async def test_update_organization_duplicate_name_returns_409(client: AsyncClient) -> None:
    """Un PATCH vers un nom déjà enregistré est refusé en conflit (FR-012)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    created: dict[str, Any]
    owner: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Occuper un nom et créer la cible du PATCH → deux organisations distinctes
    owner = await _create_user(client, "renamer@example.com")
    await _create_organization(client, "Taken Corp", owner["id"])
    created = await _create_organization(client, "Free Corp", owner["id"])

    # [STEP 2] Patcher la cible vers le nom occupé → 409, détail explicite
    response = await client.patch(
        f"/api/v1/organizations/{created['id']}", json={"name": "Taken Corp"}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Organization name already taken"


async def test_update_organization_partial_patch_updates_only_given_fields(
    client: AsyncClient,
) -> None:
    """Seuls les champs présents dans le corps changent (sémantique exclude_unset)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    body: dict[str, Any]
    created: dict[str, Any]
    owner: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Créer l'organisation cible → état initial connu
    owner = await _create_user(client, "dave-org@example.com")
    created = await _create_organization(client, "Dave Corp", owner["id"])

    # [STEP 2] Patcher uniquement name → 200, le propriétaire reste intact
    response = await client.patch(
        f"/api/v1/organizations/{created['id']}", json={"name": "Dave Corp Renamed"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Dave Corp Renamed"
    assert body["owner_id"] == owner["id"]
    assert body["id"] == created["id"]


async def test_update_organization_unknown_id_returns_404(client: AsyncClient) -> None:
    """Patcher un id inconnu répond 404 sans effet de bord (FR-003)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Patcher un id jamais attribué → 404, détail nommant l'entité
    response = await client.patch("/api/v1/organizations/999", json={"name": "Nobody Corp"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Organization 999 not found"
