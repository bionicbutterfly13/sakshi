.PHONY: help all setup docs-serve docs-build fmt fmt-check lint typecheck test coverage compile hygiene ci

PYTHON ?= python
COVERAGE_MIN ?= 88

help:
	@echo "Targets: setup, docs-serve, docs-build, fmt, fmt-check, lint, typecheck, test, coverage, compile, hygiene, ci, all"

setup:
	$(PYTHON) -m pip install -e .[dev]

docs-serve:
	$(PYTHON) -m mkdocs serve

docs-build:
	$(PYTHON) -m mkdocs build --strict

fmt:
	$(PYTHON) -m ruff format sakshi tests examples

fmt-check:
	$(PYTHON) -m ruff format --check sakshi tests examples

lint:
	$(PYTHON) -m ruff check sakshi tests examples

typecheck:
	$(PYTHON) -m mypy sakshi

test:
	$(PYTHON) -m pytest tests

coverage:
	$(PYTHON) -m pytest tests --cov=sakshi --cov-report=term-missing --cov-fail-under=$(COVERAGE_MIN)

compile:
	$(PYTHON) -m compileall -q sakshi

hygiene:
	./scripts/hygiene.sh

ci:
	$(MAKE) compile
	$(MAKE) fmt-check
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) hygiene
	$(MAKE) coverage

all: ci
