# [FILE] — tests/integration/test_comments_router.py
"""Tests d'intégration du domaine comments — parcours API contre PostgreSQL réel.

Une fonction de test par scénario d'acceptation ou cas limite du contrat :
create 201, tâche ou auteur inexistant 404, get 200/404, liste filtrée par
tâche obligatoire (422 sans ``task_id``, 404 tâche inconnue, isolation du
filtre, pagination et bornes 422), PATCH du contenu 200/404, delete 204
puis 404, delete id inconnu 404, suppression de la tâche → commentaires
emportés (CASCADE, DB seule), suppression d'un auteur → 409 et rien ne
disparaît (RESTRICT + D2), et chaîne de contenance complète
projet → tâches → commentaires (premier test à trois niveaux du projet).
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


async def _create_comment(
    client: AsyncClient, author_id: int, task_id: int, content: str
) -> dict[str, Any]:
    """Crée un commentaire via l'API et retourne le corps de la réponse 201.

    Invariant : un échec de création fait échouer immédiatement le test
    appelant (assertion sur le statut) — jamais d'état partiel silencieux.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    body: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Poster le contenu sur la tâche et l'auteur fournis → commentaire persisté
    response = await client.post(
        "/api/v1/comments",
        json={"author_id": author_id, "content": content, "task_id": task_id},
    )
    assert response.status_code == 201
    body = response.json()
    return body


async def _create_comment_fixture_chain(client: AsyncClient, tag: str) -> dict[str, Any]:
    """Crée la chaîne propriétaire → organisation → projet → tâche plus un auteur.

    Retourne ``{"author", "project", "task"}`` : l'auteur est un
    utilisateur distinct du propriétaire, sans organisation — seuls ses
    commentaires peuvent bloquer sa suppression. Invariant : ``tag`` rend
    l'email et les noms uniques au test appelant — aucune collision
    d'unicité entre scénarios d'un même fichier.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    author: dict[str, Any]
    organization: dict[str, Any]
    owner: dict[str, Any]
    project: dict[str, Any]
    task: dict[str, Any]
    # ─────────────────────────────────

    # [STEP 1] Créer le propriétaire, l'organisation et le projet → parents posés
    owner = await _create_user(client, f"{tag}@example.com")
    organization = await _create_organization(client, f"{tag} Corp", owner["id"])
    project = await _create_project(client, f"{tag} Scope", organization["id"])

    # [STEP 2] Créer la tâche et l'auteur sans organisation → cibles des commentaires
    task = await _create_task(client, project["id"], f"{tag} Task")
    author = await _create_user(client, f"{tag}-author@example.com")
    return {"author": author, "project": project, "task": task}


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


async def test_create_comment_returns_201(client: AsyncClient) -> None:
    """La création répond 201 avec le contrat CommentRead complet."""
    # ─── VARIABLE DECLARATION ZONE ───
    body: dict[str, Any]
    chain: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Poser la tâche et l'auteur → les deux FK sont disponibles
    chain = await _create_comment_fixture_chain(client, "acme-comment")

    # [STEP 2] Poster le commentaire → 201, contrat CommentRead respecté
    response = await client.post(
        "/api/v1/comments",
        json={
            "author_id": chain["author"]["id"],
            "content": "First comment.",
            "task_id": chain["task"]["id"],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["author_id"] == chain["author"]["id"]
    assert body["content"] == "First comment."
    assert body["task_id"] == chain["task"]["id"]
    assert isinstance(body["id"], int)
    assert "created_at" in body
    assert "updated_at" in body


async def test_create_comment_unknown_author_returns_404(client: AsyncClient) -> None:
    """Un auteur inexistant est refusé en 404 nommant l'entité User (D2)."""
    # ─── VARIABLE DECLARATION ZONE ───
    chain: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Poster un commentaire d'un auteur jamais attribué → 404, détail nommé
    chain = await _create_comment_fixture_chain(client, "ghost-author")
    response = await client.post(
        "/api/v1/comments",
        json={"author_id": 999, "content": "Orphan.", "task_id": chain["task"]["id"]},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User 999 not found"


async def test_create_comment_unknown_task_returns_404(client: AsyncClient) -> None:
    """Une tâche inexistante est refusée en 404 nommant l'entité Task (D2)."""
    # ─── VARIABLE DECLARATION ZONE ───
    author: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Poster un commentaire vers une tâche jamais attribuée → 404, détail nommé
    author = await _create_user(client, "ghost-task-author@example.com")
    response = await client.post(
        "/api/v1/comments",
        json={"author_id": author["id"], "content": "Orphan.", "task_id": 999},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Task 999 not found"


async def test_delete_author_with_comments_returns_409(client: AsyncClient) -> None:
    """Supprimer un auteur de commentaires est refusé en 409 — rien ne disparaît.

    Sens du RESTRICT : le refus est applicatif (SELECT avant DELETE, D2),
    la FK ``RESTRICT`` reste le backstop — l'utilisateur ET ses
    commentaires subsistent intégralement après le refus.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    chain: dict[str, Any]
    comment: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Créer un commentaire d'un auteur sans organisation → seul blocage possible
    chain = await _create_comment_fixture_chain(client, "blocked-author")
    comment = await _create_comment(
        client, chain["author"]["id"], chain["task"]["id"], "Blocking comment."
    )

    # [STEP 2] Supprimer l'auteur → 409, détail nommant le blocage par commentaires
    response = await client.delete(f"/api/v1/users/{chain['author']['id']}")
    assert response.status_code == 409
    assert response.json()["detail"] == f"User {chain['author']['id']} still has comments"

    # [STEP 3] Consulter l'auteur et le commentaire → 200, tous deux subsistent
    response = await client.get(f"/api/v1/users/{chain['author']['id']}")
    assert response.status_code == 200
    response = await client.get(f"/api/v1/comments/{comment['id']}")
    assert response.status_code == 200


async def test_delete_comment_removes_comment(client: AsyncClient) -> None:
    """La suppression répond 204 sans corps, puis la consultation répond 404."""
    # ─── VARIABLE DECLARATION ZONE ───
    chain: dict[str, Any]
    created: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Créer puis supprimer le commentaire → 204, corps vide
    chain = await _create_comment_fixture_chain(client, "temp-comment")
    created = await _create_comment(
        client, chain["author"]["id"], chain["task"]["id"], "Temp comment."
    )
    response = await client.delete(f"/api/v1/comments/{created['id']}")
    assert response.status_code == 204
    assert response.content == b""

    # [STEP 2] Consulter l'id supprimé → 404, la suppression est effective
    response = await client.get(f"/api/v1/comments/{created['id']}")
    assert response.status_code == 404


async def test_delete_comment_unknown_id_returns_404(client: AsyncClient) -> None:
    """Supprimer un id inconnu répond 404 sans effet de bord (FR-003)."""
    # ─── VARIABLE DECLARATION ZONE ───
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Supprimer un id jamais attribué → 404, détail nommant l'entité
    response = await client.delete("/api/v1/comments/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Comment 999 not found"


async def test_delete_project_cascades_to_tasks_and_comments(client: AsyncClient) -> None:
    """Supprimer un projet emporte ses tâches et leurs commentaires — chaîne complète.

    Premier test à trois niveaux du projet : la cascade descend
    projet → tâches → commentaires par la DB seule (deux FK ``CASCADE``
    enchaînées), sans aucun SELECT applicatif intermédiaire.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    chain: dict[str, Any]
    comment: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Créer projet, tâche et commentaire → chaîne de contenance posée
    chain = await _create_comment_fixture_chain(client, "chain-cascade")
    comment = await _create_comment(
        client, chain["author"]["id"], chain["task"]["id"], "Doomed with the project."
    )

    # [STEP 2] Supprimer le projet → 204, la double cascade DB emporte tout l'aval
    response = await client.delete(f"/api/v1/projects/{chain['project']['id']}")
    assert response.status_code == 204

    # [STEP 3] Consulter la tâche puis le commentaire → 404, tout l'aval a disparu
    response = await client.get(f"/api/v1/tasks/{chain['task']['id']}")
    assert response.status_code == 404
    response = await client.get(f"/api/v1/comments/{comment['id']}")
    assert response.status_code == 404


async def test_delete_task_cascades_to_comments(client: AsyncClient) -> None:
    """Supprimer une tâche emporte ses commentaires — cascade portée par la DB seule.

    Sens de la cascade : tasks → comments, jamais l'inverse — la tâche ne
    bloque pas sur ses commentaires.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    chain: dict[str, Any]
    comment: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Créer une tâche et son commentaire → axe de contenance posé
    chain = await _create_comment_fixture_chain(client, "cascade-comment")
    comment = await _create_comment(
        client, chain["author"]["id"], chain["task"]["id"], "Doomed comment."
    )

    # [STEP 2] Supprimer la tâche → 204, la cascade DB emporte le commentaire
    response = await client.delete(f"/api/v1/tasks/{chain['task']['id']}")
    assert response.status_code == 204

    # [STEP 3] Consulter le commentaire → 404, disparu avec sa tâche
    response = await client.get(f"/api/v1/comments/{comment['id']}")
    assert response.status_code == 404


async def test_get_comment_returns_200(client: AsyncClient) -> None:
    """La consultation restitue exactement l'état renvoyé à la création."""
    # ─── VARIABLE DECLARATION ZONE ───
    chain: dict[str, Any]
    created: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Créer puis consulter le commentaire → 200, corps identique au créé
    chain = await _create_comment_fixture_chain(client, "carol-comment")
    created = await _create_comment(
        client, chain["author"]["id"], chain["task"]["id"], "Carol comment."
    )
    response = await client.get(f"/api/v1/comments/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


async def test_get_comment_unknown_id_returns_404(client: AsyncClient) -> None:
    """Consulter un id inconnu répond 404 avec un détail explicite (FR-003)."""
    # ─── VARIABLE DECLARATION ZONE ───
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Consulter un id jamais attribué → 404, détail nommant l'entité
    response = await client.get("/api/v1/comments/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Comment 999 not found"


async def test_list_comments_applies_pagination_bounds(client: AsyncClient) -> None:
    """``limit`` et ``offset`` découpent la liste de la tâche triée par id croissant."""
    # ─── VARIABLE DECLARATION ZONE ───
    chain: dict[str, Any]
    index: int
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Créer trois commentaires sur la même tâche → ids 1, 2, 3
    chain = await _create_comment_fixture_chain(client, "pager-comment")
    for index in range(3):
        await _create_comment(
            client, chain["author"]["id"], chain["task"]["id"], f"Comment {index}"
        )

    # [STEP 2] Demander la page limit=1 offset=1 → uniquement le deuxième commentaire
    response = await client.get(
        "/api/v1/comments",
        params={"limit": 1, "offset": 1, "task_id": chain["task"]["id"]},
    )
    assert response.status_code == 200
    assert [comment["content"] for comment in response.json()] == ["Comment 1"]


async def test_list_comments_filters_by_task(client: AsyncClient) -> None:
    """La liste restitue les commentaires de la tâche demandée — et uniquement elle."""
    # ─── VARIABLE DECLARATION ZONE ───
    chain: dict[str, Any]
    other_task: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Commenter deux tâches distinctes → un commentaire de chaque côté
    chain = await _create_comment_fixture_chain(client, "filter-comment")
    other_task = await _create_task(client, chain["project"]["id"], "Other Task")
    await _create_comment(client, chain["author"]["id"], chain["task"]["id"], "On first task.")
    await _create_comment(client, chain["author"]["id"], other_task["id"], "On other task.")

    # [STEP 2] Lister la première tâche → uniquement son commentaire, rien de l'autre
    response = await client.get("/api/v1/comments", params={"task_id": chain["task"]["id"]})
    assert response.status_code == 200
    assert [comment["content"] for comment in response.json()] == ["On first task."]


async def test_list_comments_rejects_out_of_bounds_pagination(client: AsyncClient) -> None:
    """Des bornes hors contrat (limit 0 ou 101, offset négatif) répondent 422."""
    # ─── VARIABLE DECLARATION ZONE ───
    chain: dict[str, Any]
    params: dict[str, int]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Soumettre chaque borne invalide avec task_id valide → 422 systématique
    chain = await _create_comment_fixture_chain(client, "bounds-comment")
    for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}):
        response = await client.get(
            "/api/v1/comments", params={**params, "task_id": chain["task"]["id"]}
        )
        assert response.status_code == 422


async def test_list_comments_requires_task_id(client: AsyncClient) -> None:
    """Lister sans ``task_id`` répond 422 — jamais de liste globale (FR-021)."""
    # ─── VARIABLE DECLARATION ZONE ───
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Lister sans paramètre task_id → 422, validation du routeur
    response = await client.get("/api/v1/comments")
    assert response.status_code == 422


async def test_list_comments_unknown_task_returns_404(client: AsyncClient) -> None:
    """Lister une tâche inexistante répond 404 nommant l'entité Task (D2)."""
    # ─── VARIABLE DECLARATION ZONE ───
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Lister une tâche jamais attribuée → 404, détail nommé
    response = await client.get("/api/v1/comments", params={"task_id": 999})
    assert response.status_code == 404
    assert response.json()["detail"] == "Task 999 not found"


async def test_update_comment_unknown_id_returns_404(client: AsyncClient) -> None:
    """Patcher un id inconnu répond 404 sans effet de bord (FR-003)."""
    # ─── VARIABLE DECLARATION ZONE ───
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Patcher un id jamais attribué → 404, détail nommant l'entité
    response = await client.patch("/api/v1/comments/999", json={"content": "Nobody."})
    assert response.status_code == 404
    assert response.json()["detail"] == "Comment 999 not found"


async def test_update_comment_updates_only_content(client: AsyncClient) -> None:
    """Le PATCH ne change que le contenu — tâche et auteur restent fixés."""
    # ─── VARIABLE DECLARATION ZONE ───
    body: dict[str, Any]
    chain: dict[str, Any]
    created: dict[str, Any]
    response: Response
    # ─────────────────────────────────

    # [STEP 1] Créer un commentaire → état initial connu
    chain = await _create_comment_fixture_chain(client, "editor-comment")
    created = await _create_comment(
        client, chain["author"]["id"], chain["task"]["id"], "Initial content."
    )

    # [STEP 2] Patcher le contenu → 200, contenu remplacé, parents intacts
    response = await client.patch(
        f"/api/v1/comments/{created['id']}", json={"content": "Edited content."}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["content"] == "Edited content."
    assert body["author_id"] == created["author_id"]
    assert body["task_id"] == created["task_id"]
    assert body["id"] == created["id"]
