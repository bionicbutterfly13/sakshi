# Release Checklist

Sakshi is published to PyPI under the distribution name `pysakshi`. The
importable module remains `sakshi`. Use this checklist before making the
repository public, creating a GitHub release, or uploading to TestPyPI / PyPI.

## Pre-Release Gate

- [ ] Confirm the release version in `pyproject.toml`.
- [ ] Confirm the release version in `CITATION.cff`.
- [ ] Move the relevant `CHANGELOG.md` entries from `Unreleased` to a dated
  release section.
- [ ] Run the local verification suite:

```bash
make PYTHON=python all
python -m pip install --dry-run .
python -m build
python -m twine check dist/*
```

- [ ] Confirm GitHub Actions CI is green on the release commit.
- [ ] Re-read `INSPIRATION.md` and `docs/principles.md` for public wording
  accuracy.
- [ ] Confirm no host-application dependencies are present in package core.
- [ ] Confirm package hygiene:

```bash
./scripts/hygiene.sh
```

## GitHub Release

- [ ] Create an annotated tag matching the package version.
- [ ] Create a GitHub release from that tag.
- [ ] Mark it as prerelease while the API is still 0.x experimental.
- [ ] Include:
  - package status
  - supported Python versions
  - verification commands
  - provenance note pointing to `INSPIRATION.md`

## TestPyPI / PyPI

- [ ] Publish to TestPyPI first (`gh workflow run release.yml -f target=testpypi`).
- [ ] Install from TestPyPI into a clean virtual environment
  (`pip install --index-url https://test.pypi.org/simple/ pysakshi`).
- [ ] Run a minimal import and cycle smoke:

```python
import asyncio

from sakshi.protocols import NoOpEventBus
from sakshi.registries import PhaseRegistry


async def smoke() -> None:
    registry = PhaseRegistry(event_bus=NoOpEventBus())
    await registry.start_cycle("cycle-001")
    await registry.record_phase_output("PERCEIVE", {"ok": True})
    trace = await registry.finalize_cycle()
    assert trace.cycle_id == "cycle-001"


asyncio.run(smoke())
```

- [ ] Publish to PyPI only after the TestPyPI install works.

## Downstream Pin

After any code-bearing release commit, update downstream Git pins such as the
host applications that consume Sakshi. Docs-only releases do not require
downstream pin updates unless a downstream repository wants to point at the
latest public surface.
