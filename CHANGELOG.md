# Changelog

All notable changes to this project will be documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow
[Semantic Versioning](https://semver.org/) once 1.0 ships; until then 0.x
releases may break public API in any minor version.

## [Unreleased]

### Added
- Initial repository skeleton.
- Public protocols: `EventBus`, `Clock`, `GoalStateStore`, `BasinHook`, `WriteGuard`.
- Error hierarchy: `SakshiError` and named subclasses.
- `SakshiConfig` skeleton.
- Pydantic DTOs for goals, cycle traces, blackboard snapshots, expectations, anomalies, execution summaries, and world state.
- Core runtime packages for cycle state, registries, world simulation, interpretation, goals, plans, metacognition, and instruction intake.
- Agent-first repository contract: `AGENTS.md`, architecture/principles/quality docs, `Makefile`, and hygiene checks.
