# [FILE] — tests/integration/test_projects_router.py
"""Tests d'intégration du domaine projects — parcours API contre PostgreSQL réel.

Une fonction de test par scénario d'acceptation ou cas limite du contrat :
create 201 (description par défaut), organisation inexistante 404, doublon
de nom dans la même organisation 409 mais homonyme dans une autre 201,
get 200/404, liste et pagination (défauts, bornes, 422), PATCH partiel
200/404/409, delete 204 puis 404, delete id inconnu 404, suppression d'une
organisation occupée refusée en 409 (RESTRICT — la cascade ne descend que
de projects vers tasks/comments, jamais vers l'organisation).
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


async def _create_project(client: AsyncClient, name: str, organization_id: int) -> dict[str, Any]:
    """Crée un projet via l'API et retourne le corps de la réponse 201.

    Invariant : un échec de création fait échouer immédiatement le test
    appelant (assertion sur le statut) — jamais d'état partiel silencieux.
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    body: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Poster le nom et l'organisation fournis → projet persisté
    response = await client.post(
        "/api/v1/projects", json={"name": name, "organization_id": organization_id}
    )
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


async def test_create_project_duplicate_name_in_same_organization_returns_409(
    client: AsyncClient,
) -> None:
    """Un second projet homonyme dans la même organisation est refusé en conflit (D14)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    organization: dict[str, Any]
    owner: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Occuper le nom dans l'organisation → première création persistée
    owner = await _create_user(client, "dup-project@example.com")
    organization = await _create_organization(client, "Dup Corp", owner["id"])
    await _create_project(client, "Alpha Scope", organization["id"])

    # [STEP 2] Re-soumettre le même nom dans la même organisation → 409, détail explicite
    response = await client.post(
        "/api/v1/projects", json={"name": "Alpha Scope", "organization_id": organization["id"]}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Project name already taken in this organization"


async def test_create_project_returns_201_with_organization(client: AsyncClient) -> None:
    """La création répond 201 avec id, organisation, description par défaut et horodatages."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    body: dict[str, Any]
    organization: dict[str, Any]
    owner: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Créer la chaîne propriétaire → organisation → projet → 201 attendu
    owner = await _create_user(client, "acme-project@example.com")
    organization = await _create_organization(client, "Acme Corp", owner["id"])
    response = await client.post(
        "/api/v1/projects", json={"name": "Alpha Scope", "organization_id": organization["id"]}
    )
    assert response.status_code == 201

    # [STEP 2] Inspecter le corps → contrat ProjectRead respecté, description par défaut
    body = response.json()
    assert body["name"] == "Alpha Scope"
    assert body["description"] == ""
    assert body["organization_id"] == organization["id"]
    assert isinstance(body["id"], int)
    assert "created_at" in body
    assert "updated_at" in body


async def test_create_project_same_name_in_other_organization_returns_201(
    client: AsyncClient,
) -> None:
    """L'unicité du nom est locale à l'organisation : un homonyme ailleurs passe (D14)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    first_org: dict[str, Any]
    owner: dict[str, Any]
    response: Response
    second_org: dict[str, Any]
    # ─────────────────────────────────────────

    # [STEP 1] Occuper le nom dans une première organisation → doublon local posé
    owner = await _create_user(client, "twin-project@example.com")
    first_org = await _create_organization(client, "First Corp", owner["id"])
    await _create_project(client, "Alpha Scope", first_org["id"])

    # [STEP 2] Poster le même nom dans une autre organisation → 201, aucune collision
    second_org = await _create_organization(client, "Second Corp", owner["id"])
    response = await client.post(
        "/api/v1/projects", json={"name": "Alpha Scope", "organization_id": second_org["id"]}
    )
    assert response.status_code == 201
    assert response.json()["organization_id"] == second_org["id"]


async def test_create_project_unknown_organization_returns_404(client: AsyncClient) -> None:
    """Une organisation inexistante est refusée en 404 avant toute écriture (D2)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Poster un projet vers une organisation jamais attribuée → 404, détail nommé
    response = await client.post(
        "/api/v1/projects", json={"name": "Ghost Scope", "organization_id": 999}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Organization 999 not found"


async def test_delete_organization_with_projects_returns_409(client: AsyncClient) -> None:
    """Supprimer une organisation contenant un projet est refusé en conflit (D2).

    Sens de la cascade : la suppression d'organisation est BLOQUÉE par ses
    projets (SELECT applicatif + FK ``RESTRICT`` en backstop) — seule la
    suppression de projet cascadera vers tasks/comments (Jalons 7–8).
    """
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    organization: dict[str, Any]
    owner: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Créer une organisation et son projet → FK organization_id posée
    owner = await _create_user(client, "held-org@example.com")
    organization = await _create_organization(client, "Held Corp", owner["id"])
    await _create_project(client, "Held Scope", organization["id"])

    # [STEP 2] Tenter de supprimer l'organisation → 409, l'organisation subsiste
    response = await client.delete(f"/api/v1/organizations/{organization['id']}")
    assert response.status_code == 409
    assert response.json()["detail"] == f"Organization {organization['id']} still has projects"

    # [STEP 3] Consulter l'organisation → 200, aucune suppression partielle
    response = await client.get(f"/api/v1/organizations/{organization['id']}")
    assert response.status_code == 200


async def test_delete_project_removes_project(client: AsyncClient) -> None:
    """La suppression répond 204 sans corps, puis la consultation répond 404."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    created: dict[str, Any]
    organization: dict[str, Any]
    owner: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Créer puis supprimer le projet → 204, corps vide
    owner = await _create_user(client, "temp-project@example.com")
    organization = await _create_organization(client, "Temp Corp", owner["id"])
    created = await _create_project(client, "Temp Scope", organization["id"])
    response = await client.delete(f"/api/v1/projects/{created['id']}")
    assert response.status_code == 204
    assert response.content == b""

    # [STEP 2] Consulter l'id supprimé → 404, la suppression est effective
    response = await client.get(f"/api/v1/projects/{created['id']}")
    assert response.status_code == 404


async def test_delete_project_unknown_id_returns_404(client: AsyncClient) -> None:
    """Supprimer un id inconnu répond 404 sans effet de bord (FR-003)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Supprimer un id jamais attribué → 404, détail nommant l'entité
    response = await client.delete("/api/v1/projects/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Project 999 not found"


async def test_get_project_returns_200(client: AsyncClient) -> None:
    """La consultation restitue exactement l'état renvoyé à la création."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    created: dict[str, Any]
    organization: dict[str, Any]
    owner: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Créer puis consulter le projet → 200, corps identique au créé
    owner = await _create_user(client, "carol-project@example.com")
    organization = await _create_organization(client, "Carol Corp", owner["id"])
    created = await _create_project(client, "Carol Scope", organization["id"])
    response = await client.get(f"/api/v1/projects/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


async def test_get_project_unknown_id_returns_404(client: AsyncClient) -> None:
    """Consulter un id inconnu répond 404 avec un détail explicite (FR-003)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Consulter un id jamais attribué → 404, détail nommant l'entité
    response = await client.get("/api/v1/projects/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Project 999 not found"


async def test_list_projects_applies_pagination_bounds(client: AsyncClient) -> None:
    """``limit`` et ``offset`` découpent la liste triée par id croissant."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    index: int
    organization: dict[str, Any]
    owner: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Créer trois projets → ids 1, 2, 3 (identités remises à zéro)
    owner = await _create_user(client, "pager-project@example.com")
    organization = await _create_organization(client, "Pager Corp", owner["id"])
    for index in range(3):
        await _create_project(client, f"Scope {index}", organization["id"])

    # [STEP 2] Demander la page limit=1 offset=1 → uniquement le deuxième projet
    response = await client.get("/api/v1/projects", params={"limit": 1, "offset": 1})
    assert response.status_code == 200
    assert [project["name"] for project in response.json()] == ["Scope 1"]


async def test_list_projects_rejects_out_of_bounds_pagination(client: AsyncClient) -> None:
    """Des bornes hors contrat (limit 0 ou 101, offset négatif) répondent 422."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    params: dict[str, int]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Soumettre chaque borne invalide → 422 systématique, aucune lecture
    for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}):
        response = await client.get("/api/v1/projects", params=params)
        assert response.status_code == 422


async def test_list_projects_returns_default_page(client: AsyncClient) -> None:
    """Sans paramètres : liste vide valide, puis page par défaut triée par id."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    organization: dict[str, Any]
    owner: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Lister une base vide → 200 et collection vide, pas une erreur
    response = await client.get("/api/v1/projects")
    assert response.status_code == 200
    assert response.json() == []

    # [STEP 2] Créer deux projets et relister → défauts appliqués, tri par id
    owner = await _create_user(client, "lister-project@example.com")
    organization = await _create_organization(client, "Lister Corp", owner["id"])
    await _create_project(client, "Alpha Scope", organization["id"])
    await _create_project(client, "Beta Scope", organization["id"])
    response = await client.get("/api/v1/projects")
    assert response.status_code == 200
    assert [project["name"] for project in response.json()] == [
        "Alpha Scope",
        "Beta Scope",
    ]


async def test_update_project_duplicate_name_returns_409(client: AsyncClient) -> None:
    """Un PATCH vers un nom déjà pris dans la même organisation est refusé (D14)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    created: dict[str, Any]
    organization: dict[str, Any]
    owner: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Occuper un nom et créer la cible du PATCH → deux projets dans la même org
    owner = await _create_user(client, "renamer-project@example.com")
    organization = await _create_organization(client, "Renamer Corp", owner["id"])
    await _create_project(client, "Taken Scope", organization["id"])
    created = await _create_project(client, "Free Scope", organization["id"])

    # [STEP 2] Patcher la cible vers le nom occupé → 409, détail explicite
    response = await client.patch(f"/api/v1/projects/{created['id']}", json={"name": "Taken Scope"})
    assert response.status_code == 409
    assert response.json()["detail"] == "Project name already taken in this organization"


async def test_update_project_partial_patch_updates_only_given_fields(
    client: AsyncClient,
) -> None:
    """Seuls les champs présents dans le corps changent (sémantique exclude_unset)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    body: dict[str, Any]
    created: dict[str, Any]
    organization: dict[str, Any]
    owner: dict[str, Any]
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Créer le projet cible → état initial connu
    owner = await _create_user(client, "dave-project@example.com")
    organization = await _create_organization(client, "Dave Corp", owner["id"])
    created = await _create_project(client, "Dave Scope", organization["id"])

    # [STEP 2] Patcher uniquement description → 200, nom et organisation intacts
    response = await client.patch(
        f"/api/v1/projects/{created['id']}", json={"description": "Refonte du pipeline"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "Refonte du pipeline"
    assert body["name"] == "Dave Scope"
    assert body["organization_id"] == organization["id"]
    assert body["id"] == created["id"]


async def test_update_project_unknown_id_returns_404(client: AsyncClient) -> None:
    """Patcher un id inconnu répond 404 sans effet de bord (FR-003)."""
    # ─── ZONE DE DÉCLARATION DES VARIABLES ───
    response: Response
    # ─────────────────────────────────────────

    # [STEP 1] Patcher un id jamais attribué → 404, détail nommant l'entité
    response = await client.patch("/api/v1/projects/999", json={"name": "Nobody Scope"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Project 999 not found"
