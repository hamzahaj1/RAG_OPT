COMPOSE := podman compose

.PHONY: help up down logs db-migrate db-revision db-seed rag-annotate rag-check

.DEFAULT_GOAL := help

help:
	@echo "Cibles disponibles :"
	@echo "  make up          - Démarre l'infrastructure (PostgreSQL, Adminer)"
	@echo "  make down        - Arrête l'infrastructure"
	@echo "  make logs        - Affiche les logs de l'infrastructure"
	@echo "  make db-migrate  - Applique les migrations Alembic"
	@echo "  make db-revision - Génère une migration (m=\"message\") et la met aux normes Ruff"
	@echo "  make db-seed     - Peuple la base de données (Phase 2, Jalon 9)"
	@echo "  make rag-annotate - Régénère les annotations RAG du corpus app/ (Phase 3)"
	@echo "  make rag-check   - Annotation + git diff --exit-code (contrôle de dérive RAG)"

up:
	$(COMPOSE) up -d
	@echo "✓ PostgreSQL démarré sur localhost:5432"
	@echo "✓ Adminer démarré sur http://localhost:8080"

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

db-migrate:
	poetry run alembic upgrade head
	@echo "✓ Migrations appliquées"

db-revision:
ifndef m
	$(error Usage : make db-revision m="message_de_migration")
endif
	poetry run alembic revision --autogenerate -m "$(m)"
	poetry run ruff format alembic/versions/
	poetry run ruff check --fix alembic/versions/
	@echo "✓ Révision générée et mise aux normes Ruff"

db-seed:
	poetry run python -m app.scripts.seed

rag-annotate:
	poetry run python -m scripts.generate_topology_headers
	poetry run python -m scripts.generate_structural_metadata
	@echo "✓ Annotations RAG régénérées"

rag-check: rag-annotate
	git diff --exit-code -- app/ TOPOLOGY.yaml
	@echo "✓ Annotation à jour — aucune dérive"
