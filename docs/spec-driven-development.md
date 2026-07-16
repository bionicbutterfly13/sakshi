# Spec-Driven Development

Sakshi uses GitHub Spec Kit for new staged development work. The project was
initialized with the official Codex integration, which installs workflow skills
under `.agents/skills/` and shared scripts, templates, and governance under
`.specify/`.

## Source of Truth

- `AGENTS.md` remains the protected operational guide for coding agents.
- `.specify/memory/constitution.md` governs Spec Kit specifications, plans,
  tasks, and reviews.
- `CONTRIBUTING.md` defines contribution and branch conventions.
- `specs/<number>-<feature>/` contains active and completed Spec Kit feature
  artifacts.
- `.archive/` is excluded from Git and Graphify. Its legacy planning and internal
  disclosure material is read-only history, not active context. The eight
  completed planning tracks are not copied into `specs/`.

## Forward-Only Cutover

The migration does not rewrite completed legacy tracks. New multi-step features,
bugs, releases, and audits start in Spec Kit. Small self-contained corrections
may proceed without a feature directory when repository instructions and risk
do not require staged planning.

The normal flow is:

1. Check the constitution with `$speckit-constitution` when governance changes.
2. Create requirements with `$speckit-specify`.
3. Resolve material ambiguity with `$speckit-clarify` when needed.
4. Create the technical plan with `$speckit-plan`.
5. Generate executable tasks with `$speckit-tasks`.
6. Run `$speckit-analyze` when cross-artifact consistency needs verification.
7. Implement with `$speckit-implement` and finish with the repository quality
   gate.

Spec Kit v0.12.17 does not install the retired agent-context extension, so the
workflow has no automatic path for modifying `AGENTS.md`.
