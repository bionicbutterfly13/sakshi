# Changelog

All notable changes to this project will be documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow
[Semantic Versioning](https://semver.org/) once 1.0 ships; until then 0.x
releases may break public API in any minor version.

## [Unreleased]

## [0.3.0] - 2026-05-06

### Added
- `GoalGraph.iter_goals()` — public iterator over every goal in the
  graph regardless of status. Stable insertion order.
- `GoalGraph.get_goals_by_status(statuses)` — public filter for goals
  matching any of the supplied :class:`GoalStatus` values. Empty
  filter returns an empty list.
- `CognitiveBlackboard.snapshot` — deepcopy failures now log a warning
  with the offending key + value type instead of silently aliasing
  live state. Snapshots remain best-effort but no longer fail invisibly.
- `AnomalyExplainer.explain` — broad-except handler promoted from
  `debug` to `warning`; the degraded `AnomalyExplanation` now surfaces
  the underlying error class in its `hypothesis` text so callers can
  see when an explanation is a fallback.

### Changed
- README Status section: explicit warning that the `NoOpEventBus`,
  `NoOpBasinHook`, and `AlwaysPermitWriteGuard` defaults are inert by
  design; production hosts must inject real implementations.

## [0.2.0] - 2026-05-05

### Added
- CI `package` job: runs `python -m build` + `twine check` on every PR so
  the release path cannot drift from CI.
- `release.yml` GitHub Actions workflow: tag pushes (`v*`) build and
  publish to PyPI via Trusted Publishing (OIDC, no API token);
  `workflow_dispatch` with `target=testpypi` supports dry-run publishes to
  TestPyPI.

### Changed
- Distribution name confirmed as `pysakshi` on PyPI; `sakshi` import name
  unchanged. This release establishes the first stable PyPI pin, enabling
  host projects to drop git-commit references in favour of a versioned
  requirement (`pysakshi>=0.2.0`).

## [0.1.0] - 2026-05-04

### Added
- First public alpha release.
- Top-level re-exports from `sakshi`: `PhaseRegistry`, protocols
  (`EventBus`, `Clock`, `GoalStateStore`, `BasinHook`, `WriteGuard`),
  default no-op implementations (`NoOpEventBus`, `NoOpBasinHook`,
  `AlwaysPermitWriteGuard`), and the `SakshiError` hierarchy.
- Initial repository skeleton.
- Public protocols: `EventBus`, `Clock`, `GoalStateStore`, `BasinHook`, `WriteGuard`.
- Error hierarchy: `SakshiError` and named subclasses.
- `SakshiConfig` skeleton.
- Pydantic DTOs for goals, cycle traces, blackboard snapshots, expectations, anomalies, execution summaries, and world state.
- Core runtime packages for cycle state, registries, world simulation, interpretation, goals, plans, metacognition, and instruction intake.
- Agent-first repository contract: `AGENTS.md`, architecture/principles/quality docs, `Makefile`, and hygiene checks.
