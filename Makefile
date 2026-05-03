.PHONY: help all setup fmt fmt-check lint test compile hygiene ci

PYTHON ?= python

help:
	@echo "Targets: setup, fmt, fmt-check, lint, test, compile, hygiene, ci, all"

setup:
	$(PYTHON) -m pip install -e .[dev]

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
