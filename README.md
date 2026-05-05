# Sakshi

> Sakshi (साक्षी) is the Vedantic name for the consciousness that observes consciousness without acting.

A metacognitive runtime for Python agents: the Witness pattern. A watching process embedded in your agent that monitors plan execution, evaluates against expectations, and steers cognition without doing the cognition itself.

## Status

**0.2.0 alpha.** First version verified end-to-end against a host integration. The public API may still change in 0.x minor releases. Approaching a 1.0 freeze; not yet recommended for unverified production use.

## Install

Sakshi is published to PyPI under the distribution name `pysakshi`. The
importable module is still `sakshi`:

```bash
pip install pysakshi
```

```python
import sakshi
```

The bare name `sakshi` is reserved by an unrelated PyPI account with no
releases; once that name is recovered, `pysakshi` will become an alias.

To install the latest unreleased commit from source:

```bash
pip install git+https://github.com/bionicbutterfly13/sakshi
```

Release process: see [`docs/release-checklist.md`](docs/release-checklist.md).

## What it is

Sakshi exposes a small, opinionated set of seams a host application supplies:

- An `EventBus` for emitting cycle and goal events.
- A `Clock` for deterministic time.
- A `GoalStateStore` for fetching world state and recording goal outcomes.
- An optional `BasinHook` for hosts that maintain an attractor-basin field.
- A `WriteGuard` for routing Sakshi-originated writes through the host's safety policy.

Around these protocols Sakshi assembles a generic six-phase cognitive cycle (PERCEIVE, INTERPRET, EVAL, INTEND, PLAN, ACT) and a meta-loop (MONITOR, ASSESS, CONTROL) framed as general metacognitive phases.

## Quickstart

```python
import asyncio

from sakshi.registries import PhaseRegistry
from sakshi.protocols import NoOpEventBus


async def main() -> None:
    registry = PhaseRegistry(event_bus=NoOpEventBus())

    await registry.start_cycle("cycle-001")
    await registry.record_phase_output("PERCEIVE", {"basins": ["attention"]})
    await registry.record_phase_output("INTERPRET", {"confidence": 0.82})
    trace = await registry.finalize_cycle()

    print(trace.cycle_id)
    print([phase.phase_name for phase in trace.phase_results])


asyncio.run(main())
```

Hosts that need production side effects implement the small protocols in
`sakshi.protocols` and pass those implementations into Sakshi runtime classes.

## Influences

Sakshi draws inspiration from MIDCA-style metacognitive control loops, active-inference monitoring, and production cognitive-runtime experience. See [INSPIRATION.md](INSPIRATION.md) for the full provenance.

Sakshi is **not** a MIDCA implementation, MIDCA-compatible, or a fork of any MIDCA codebase. The MIDCA reference architecture is one influence among several.

## License

Apache-2.0. See [LICENSE](LICENSE).
