COMPOSE ?= docker compose

.PHONY: setup config up down logs ps health test

setup:
	@test -f .env || cp .env.example .env

config: setup
	$(COMPOSE) config --quiet

up: setup
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f backend

ps:
	$(COMPOSE) ps

health:
	$(COMPOSE) exec -T backend python -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8080/api/health", timeout=3).read().decode())'

test:
	python -m pytest -q
