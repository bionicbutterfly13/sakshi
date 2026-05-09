.PHONY: help all setup docs-serve docs-build fmt fmt-check lint test compile hygiene ci

PYTHON ?= python

help:
	@echo "Targets: setup, docs-serve, docs-build, fmt, fmt-check, lint, test, compile, hygiene, ci, all"

setup:
	$(PYTHON) -m pip install -e .[dev]

docs-serve:
	$(PYTHON) -m mkdocs serve

docs-build:
	$(PYTHON) -m mkdocs build --strict

fmt:
	$(PYTHON) -m ruff format sakshi tests

fmt-check:
	$(PYTHON) -m ruff format --check sakshi tests

lint:
	$(PYTHON) -m ruff check sakshi tests

test:
	$(PYTHON) -m pytest tests

compile:
	$(PYTHON) -m compileall -q sakshi

hygiene:
	./scripts/hygiene.sh

ci:
	$(MAKE) compile
	$(MAKE) fmt-check
	$(MAKE) lint
	$(MAKE) hygiene
	$(MAKE) test

all: ci
