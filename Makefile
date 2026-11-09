# Lokale Entwicklung ohne Docker: `make setup`, danach `make test`.
PY ?= $(CURDIR)/.venv/bin/python

.PHONY: setup test test-backend test-frontend test-e2e build

setup:
	python3.12 -m venv .venv
	$(PY) -m pip install -q -r backend/requirements-dev.txt
	cd frontend && npm ci && npx playwright install chromium

test: test-backend test-frontend test-e2e

test-backend:
	cd backend && $(PY) -m pytest -q

test-frontend:
	cd frontend && npm test

test-e2e:
	cd frontend && npm run build && PY=$(PY) npm run e2e

build:
	cd frontend && npm run build
