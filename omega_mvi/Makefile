PYTHON ?= python
COMPOSE ?= docker compose -f ../compose.omega.yml

.PHONY: test config up health down

test:
	$(PYTHON) -m pytest -q tests

config:
	$(COMPOSE) config -q

up:
	$(COMPOSE) up --build

health:
	curl --fail --silent --show-error http://127.0.0.1:18080/health

down:
	$(COMPOSE) down --remove-orphans
