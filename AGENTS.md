# Sakshi Agent Guide

This file is the short entry point for coding agents. It is a map, not a full manual.

## Environment

- Python: 3.11+
- Install package: `pip install -e .`
- Install dev tools: `pip install -e .[dev]`
- Main quality gate: `make all`

## Repository Map

- [README.md](README.md) — public project overview and install notes.
- [CONTRIBUTING.md](CONTRIBUTING.md) — contributor setup and branch guidance.
- [INSPIRATION.md](INSPIRATION.md) — provenance and related-work attribution.
- [docs/architecture.md](docs/architecture.md) — package layers, protocols, and failure model.
- [docs/principles.md](docs/principles.md) — non-negotiable design and identity rules.
- [docs/quality.md](docs/quality.md) — current quality status by package area.
- [scripts/hygiene.sh](scripts/hygiene.sh) — mechanical package hygiene checks.

## Required Rules

- Keep package code free of host runtime imports. `sakshi/` MUST NOT import `api.*`, FastAPI, Graphiti, Neo4j, smolagents, or a host service getter.
- Keep public identifiers product-native. Do not use external reference-architecture names in package names, import paths, class names, function names, or primary docs headings.
- Host integrations belong behind protocols. If code needs a runtime service, define or reuse a protocol and let the host adapter implement it.
- Do not add module-global singleton getters in package code. Hosts own construction and lifecycle.
- Keep changes narrow. Do not combine extraction, public API redesign, and host rewiring in one commit.
- Run `make all` before handoff when dev dependencies are installed.

## Current Migration Status

Sakshi is in early extraction. The package has a public seam, DTOs, and the foundations cluster. Remaining clusters should update `docs/quality.md` as they land.

