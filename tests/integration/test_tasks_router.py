# [FILE] — tests/integration/test_tasks_router.py
"""Tests d'intégration du domaine tasks — parcours API contre PostgreSQL réel.

Une fonction de test par scénario d'acceptation ou cas limite du contrat :
create 201 assignée et non assignée, projet ou assigné inexistant 404,
enum invalide 422, get 200/404, liste et pagination (défauts, bornes,
422), PATCH partiel 200/404, assignation puis désassignation par ``null``
explicite, delete 204 puis 404, delete id inconnu 404, suppression du
projet → tâches emportées (CASCADE, DB seule), suppression de l'assigné →
tâche conservée désassignée (SET NULL, DB seule).
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

TASK_PAYLOAD: dict[str, str] = {
    "priority": "medium",
    "status": "todo",
    "title": "Base Task",
}


async def _create_organization(client: AsyncClient, name: str, owner_id: int) -> dict[str, Any]:
    """Crée une organisation via l'API et retourne le corps de la réponse 201.

    Invariant : un échec de création fait échouer immédiatement le test
    appelant (assertion sur le statut) — jamais d'état partiel silencieux.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    body: dict[str, Any]
    response: Response
    # ─────────────────────────────────

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
    # ─── VARIABLE DECLARATION ZONE ───
    body: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Poster le nom et l'organisation fournis → projet persisté
    response = await client.post(
        "/api/v1/projects", json={"name": name, "organization_id": organization_id}
    )
    assert response.status_code == 201
    body = response.json()
    return body


async def _create_task(client: AsyncClient, project_id: int, title: str) -> dict[str, Any]:
    """Crée une tâche non assignée via l'API et retourne le corps de la réponse 201.

    Invariant : un échec de création fait échouer immédiatement le test
    appelant (assertion sur le statut) — jamais d'état partiel silencieux.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    body: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Poster le payload de référence sur le projet fourni → tâche persistée
    response = await client.post(
        "/api/v1/tasks", json={**TASK_PAYLOAD, "project_id": project_id, "title": title}
    )
    assert response.status_code == 201
    body = response.json()
    return body


async def _create_task_fixture_chain(client: AsyncClient, tag: str) -> dict[str, Any]:
    """Crée la chaîne propriétaire → organisation → projet et retourne le projet.

    Invariant : ``tag`` rend l'email et les noms uniques au test appelant —
    aucune collision d'unicité entre scénarios d'un même fichier.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    organization: dict[str, Any]
    owner: dict[str, Any]
    project: dict[str, Any]
    # ─────────────────────────────────

    # [STEP 1] Créer le propriétaire → référence users disponible
    owner = await _create_user(client, f"{tag}@example.com")

    # [STEP 2] Créer l'organisation puis le projet → parent des tâches disponible
    organization = await _create_organization(client, f"{tag} Corp", owner["id"])
    project = await _create_project(client, f"{tag} Scope", organization["id"])
    return project


async def _create_user(client: AsyncClient, email: str) -> dict[str, Any]:
    """Crée un utilisateur via l'API et retourne le corps de la réponse 201.

    Invariant : un échec de création fait échouer immédiatement le test
    appelant (assertion sur le statut) — jamais d'état partiel silencieux.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    body: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Poster le payload de référence avec l'email fourni → utilisateur persisté
    response = await client.post("/api/v1/users", json={**OWNER_PAYLOAD, "email": email})
    assert response.status_code == 201
    body = response.json()
    return body


async def test_create_task_invalid_enum_returns_422(client: AsyncClient) -> None:
    """Un statut ou une priorité hors enum est refusé en 422 par Pydantic (D1)."""
    # ─── VARIABLE DECLARATION ZONE ───
    invalid_field: dict[str, str]
    project: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Poser le projet parent → seule la validation d'enum peut échouer ensuite
    project = await _create_task_fixture_chain(client, "enum-task")

    # [STEP 2] Soumettre chaque enum invalide → 422 systématique, aucune écriture
    for invalid_field in ({"status": "archived"}, {"priority": "urgent"}):
        response = await client.post(
            "/api/v1/tasks",
            json={**TASK_PAYLOAD, **invalid_field, "project_id": project["id"]},
        )
        assert response.status_code == 422


async def test_create_task_returns_201_with_assignee(client: AsyncClient) -> None:
    """La création assignée répond 201 avec le contrat TaskRead complet."""
    # ─── VARIABLE DECLARATION ZONE ───
    assignee: dict[str, Any]
    body: dict[str, Any]
    project: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Créer le projet et un assigné distinct → les deux FK sont disponibles
    project = await _create_task_fixture_chain(client, "acme-task")
    assignee = await _create_user(client, "worker-task@example.com")

    # [STEP 2] Poster la tâche assignée → 201, contrat TaskRead respecté
    response = await client.post(
        "/api/v1/tasks",
        json={**TASK_PAYLOAD, "assignee_id": assignee["id"], "project_id": project["id"]},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["assignee_id"] == assignee["id"]
    assert body["description"] == ""
    assert body["priority"] == "medium"
    assert body["project_id"] == project["id"]
    assert body["status"] == "todo"
    assert body["title"] == "Base Task"
    assert isinstance(body["id"], int)
    assert "created_at" in body
    assert "updated_at" in body


async def test_create_task_returns_201_without_assignee(client: AsyncClient) -> None:
    """La création sans assigné répond 201 : la tâche naît libre (assignee_id null)."""
    # ─── VARIABLE DECLARATION ZONE ───
    body: dict[str, Any]
    project: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Poster une tâche sans assignee_id → 201, tâche non assignée
    project = await _create_task_fixture_chain(client, "free-task")
    response = await client.post(
        "/api/v1/tasks", json={**TASK_PAYLOAD, "project_id": project["id"]}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["assignee_id"] is None


async def test_create_task_unknown_assignee_returns_404(client: AsyncClient) -> None:
    """Un assigné inexistant est refusé en 404 nommant l'entité User (D2)."""
    # ─── VARIABLE DECLARATION ZONE ───
    project: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Poster une tâche vers un assigné jamais attribué → 404, détail nommé
    project = await _create_task_fixture_chain(client, "ghost-assignee")
    response = await client.post(
        "/api/v1/tasks",
        json={**TASK_PAYLOAD, "assignee_id": 999, "project_id": project["id"]},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User 999 not found"


async def test_create_task_unknown_project_returns_404(client: AsyncClient) -> None:
    """Un projet inexistant est refusé en 404 nommant l'entité Project (D2)."""
    # ─── VARIABLE DECLARATION ZONE ───
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Poster une tâche vers un projet jamais attribué → 404, détail nommé
    response = await client.post("/api/v1/tasks", json={**TASK_PAYLOAD, "project_id": 999})
    assert response.status_code == 404
    assert response.json()["detail"] == "Project 999 not found"


async def test_delete_assignee_sets_task_assignee_to_null(client: AsyncClient) -> None:
    """Supprimer l'assigné répond 204 et désassigne la tâche sans la détruire.

    Sens du SET NULL : porté par la DB seule (``ondelete=SET NULL``, D2) —
    aucune retouche applicative de ``delete_user`` pour ce cas.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    assignee: dict[str, Any]
    project: dict[str, Any]
    response: Response
    task: dict[str, Any]
    # ─────────────────────────────────

    # [STEP 1] Créer une tâche assignée à un utilisateur sans organisation → FK posée
    project = await _create_task_fixture_chain(client, "setnull-task")
    assignee = await _create_user(client, "leaver-task@example.com")
    response = await client.post(
        "/api/v1/tasks",
        json={**TASK_PAYLOAD, "assignee_id": assignee["id"], "project_id": project["id"]},
    )
    assert response.status_code == 201
    task = response.json()

    # [STEP 2] Supprimer l'assigné → 204, l'utilisateur ne possède aucune organisation
    response = await client.delete(f"/api/v1/users/{assignee['id']}")
    assert response.status_code == 204

    # [STEP 3] Consulter la tâche → 200, conservée mais désassignée par la DB
    response = await client.get(f"/api/v1/tasks/{task['id']}")
    assert response.status_code == 200
    assert response.json()["assignee_id"] is None


async def test_delete_project_cascades_to_tasks(client: AsyncClient) -> None:
    """Supprimer un projet emporte ses tâches — cascade portée par la DB seule.

    Sens de la cascade : projects → tasks (→ comments au Jalon 8), jamais
    l'inverse — le projet ne bloque pas sur ses tâches.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    project: dict[str, Any]
    response: Response
    task: dict[str, Any]
    # ─────────────────────────────────

    # [STEP 1] Créer un projet et sa tâche → axe de contenance posé
    project = await _create_task_fixture_chain(client, "cascade-task")
    task = await _create_task(client, project["id"], "Doomed Task")

    # [STEP 2] Supprimer le projet → 204, la cascade DB emporte la tâche
    response = await client.delete(f"/api/v1/projects/{project['id']}")
    assert response.status_code == 204

    # [STEP 3] Consulter la tâche → 404, disparue avec son projet
    response = await client.get(f"/api/v1/tasks/{task['id']}")
    assert response.status_code == 404


async def test_delete_task_removes_task(client: AsyncClient) -> None:
    """La suppression répond 204 sans corps, puis la consultation répond 404."""
    # ─── VARIABLE DECLARATION ZONE ───
    created: dict[str, Any]
    project: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Créer puis supprimer la tâche → 204, corps vide
    project = await _create_task_fixture_chain(client, "temp-task")
    created = await _create_task(client, project["id"], "Temp Task")
    response = await client.delete(f"/api/v1/tasks/{created['id']}")
    assert response.status_code == 204
    assert response.content == b""

    # [STEP 2] Consulter l'id supprimé → 404, la suppression est effective
    response = await client.get(f"/api/v1/tasks/{created['id']}")
    assert response.status_code == 404


async def test_delete_task_unknown_id_returns_404(client: AsyncClient) -> None:
    """Supprimer un id inconnu répond 404 sans effet de bord (FR-003)."""
    # ─── VARIABLE DECLARATION ZONE ───
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Supprimer un id jamais attribué → 404, détail nommant l'entité
    response = await client.delete("/api/v1/tasks/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task 999 not found"


async def test_get_task_returns_200(client: AsyncClient) -> None:
    """La consultation restitue exactement l'état renvoyé à la création."""
    # ─── VARIABLE DECLARATION ZONE ───
    created: dict[str, Any]
    project: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Créer puis consulter la tâche → 200, corps identique au créé
    project = await _create_task_fixture_chain(client, "carol-task")
    created = await _create_task(client, project["id"], "Carol Task")
    response = await client.get(f"/api/v1/tasks/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


async def test_get_task_unknown_id_returns_404(client: AsyncClient) -> None:
    """Consulter un id inconnu répond 404 avec un détail explicite (FR-003)."""
    # ─── VARIABLE DECLARATION ZONE ───
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Consulter un id jamais attribué → 404, détail nommant l'entité
    response = await client.get("/api/v1/tasks/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task 999 not found"


async def test_list_tasks_applies_pagination_bounds(client: AsyncClient) -> None:
    """``limit`` et ``offset`` découpent la liste triée par id croissant."""
    # ─── VARIABLE DECLARATION ZONE ───
    index: int
    project: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Créer trois tâches → ids 1, 2, 3 (identités remises à zéro)
    project = await _create_task_fixture_chain(client, "pager-task")
    for index in range(3):
        await _create_task(client, project["id"], f"Task {index}")

    # [STEP 2] Demander la page limit=1 offset=1 → uniquement la deuxième tâche
    response = await client.get("/api/v1/tasks", params={"limit": 1, "offset": 1})
    assert response.status_code == 200
    assert [task["title"] for task in response.json()] == ["Task 1"]


async def test_list_tasks_rejects_out_of_bounds_pagination(client: AsyncClient) -> None:
    """Des bornes hors contrat (limit 0 ou 101, offset négatif) répondent 422."""
    # ─── VARIABLE DECLARATION ZONE ───
    params: dict[str, int]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Soumettre chaque borne invalide → 422 systématique, aucune lecture
    for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}):
        response = await client.get("/api/v1/tasks", params=params)
        assert response.status_code == 422


async def test_list_tasks_returns_default_page(client: AsyncClient) -> None:
    """Sans paramètres : liste vide valide, puis page par défaut triée par id."""
    # ─── VARIABLE DECLARATION ZONE ───
    project: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Lister une base vide → 200 et collection vide, pas une erreur
    response = await client.get("/api/v1/tasks")
    assert response.status_code == 200
    assert response.json() == []

    # [STEP 2] Créer deux tâches et relister → défauts appliqués, tri par id
    project = await _create_task_fixture_chain(client, "lister-task")
    await _create_task(client, project["id"], "Alpha Task")
    await _create_task(client, project["id"], "Beta Task")
    response = await client.get("/api/v1/tasks")
    assert response.status_code == 200
    assert [task["title"] for task in response.json()] == [
        "Alpha Task",
        "Beta Task",
    ]


async def test_update_task_assigns_then_unassigns_via_explicit_null(client: AsyncClient) -> None:
    """L'assignation puis la désassignation passent par le même PATCH partiel.

    Point délicat du contrat : ``{"assignee_id": null}`` explicitement
    fourni désassigne (SET NULL applicatif), tandis qu'un PATCH sans le
    champ — couvert par le test de PATCH partiel — ne change rien.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    assignee: dict[str, Any]
    project: dict[str, Any]
    response: Response
    task: dict[str, Any]
    # ─────────────────────────────────

    # [STEP 1] Créer une tâche libre et un assigné → état initial non assigné
    project = await _create_task_fixture_chain(client, "assign-task")
    assignee = await _create_user(client, "cycler-task@example.com")
    task = await _create_task(client, project["id"], "Cycled Task")
    assert task["assignee_id"] is None

    # [STEP 2] Patcher assignee_id vers l'utilisateur → 200, tâche assignée
    response = await client.patch(
        f"/api/v1/tasks/{task['id']}", json={"assignee_id": assignee["id"]}
    )
    assert response.status_code == 200
    assert response.json()["assignee_id"] == assignee["id"]

    # [STEP 3] Patcher un null explicite → 200, tâche désassignée
    response = await client.patch(f"/api/v1/tasks/{task['id']}", json={"assignee_id": None})
    assert response.status_code == 200
    assert response.json()["assignee_id"] is None


async def test_update_task_partial_patch_updates_only_given_fields(client: AsyncClient) -> None:
    """Seuls les champs présents dans le corps changent (sémantique exclude_unset)."""
    # ─── VARIABLE DECLARATION ZONE ───
    assignee: dict[str, Any]
    body: dict[str, Any]
    project: dict[str, Any]
    response: Response
    task: dict[str, Any]
    # ─────────────────────────────────

    # [STEP 1] Créer une tâche assignée → état initial connu, assignation posée
    project = await _create_task_fixture_chain(client, "dave-task")
    assignee = await _create_user(client, "keeper-task@example.com")
    response = await client.post(
        "/api/v1/tasks",
        json={**TASK_PAYLOAD, "assignee_id": assignee["id"], "project_id": project["id"]},
    )
    assert response.status_code == 201
    task = response.json()

    # [STEP 2] Patcher uniquement status → 200, assignation et autres champs intacts
    response = await client.patch(f"/api/v1/tasks/{task['id']}", json={"status": "in_progress"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["assignee_id"] == assignee["id"]
    assert body["priority"] == task["priority"]
    assert body["title"] == task["title"]
    assert body["id"] == task["id"]


async def test_update_task_unknown_assignee_returns_404(client: AsyncClient) -> None:
    """Patcher vers un assigné inexistant répond 404 sans modifier la tâche (D2)."""
    # ─── VARIABLE DECLARATION ZONE ───
    project: dict[str, Any]
    response: Response
    task: dict[str, Any]
    # ─────────────────────────────────

    # [STEP 1] Créer une tâche libre → cible du PATCH posée
    project = await _create_task_fixture_chain(client, "ghost-patch")
    task = await _create_task(client, project["id"], "Ghost Patch Task")

    # [STEP 2] Patcher vers un assigné jamais attribué → 404, tâche toujours libre
    response = await client.patch(f"/api/v1/tasks/{task['id']}", json={"assignee_id": 999})
    assert response.status_code == 404
    assert response.json()["detail"] == "User 999 not found"
    response = await client.get(f"/api/v1/tasks/{task['id']}")
    assert response.json()["assignee_id"] is None


async def test_update_task_unknown_id_returns_404(client: AsyncClient) -> None:
    """Patcher un id inconnu répond 404 sans effet de bord (FR-003)."""
    # ─── VARIABLE DECLARATION ZONE ───
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Patcher un id jamais attribué → 404, détail nommant l'entité
    response = await client.patch("/api/v1/tasks/999", json={"title": "Nobody Task"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Task 999 not found"
