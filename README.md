# Sakshi

> Sakshi (साक्षी) is the Vedantic name for the consciousness that observes consciousness without acting.

A metacognitive runtime for Python agents: the Witness pattern. A watching process embedded in your agent that monitors plan execution, evaluates against expectations, and steers cognition without doing the cognition itself.

## Status

**0.x experimental.** The public API may change in any minor release. Not yet recommended for production use.

## Install

```bash
pip install sakshi
```

(Not yet on PyPI; currently in early development.)

## What it is

Sakshi exposes a small, opinionated set of seams a host application supplies:

- An `EventBus` for emitting cycle and goal events.
- A `Clock` for deterministic time.
- A `GoalStateStore` for fetching world state and recording goal outcomes.
- An optional `BasinHook` for hosts that maintain an attractor-basin field.
- A `WriteGuard` for routing Sakshi-originated writes through the host's safety policy.

Around these protocols Sakshi assembles a generic six-phase cognitive cycle (PERCEIVE, INTERPRET, EVAL, INTEND, PLAN, ACT) and a meta-loop (MONITOR, ASSESS, CONTROL) framed as general metacognitive phases.

## Quickstart

Coming in a later release. The public API is still being shaped.

## Influences

Sakshi draws inspiration from MIDCA-style metacognitive control loops, active-inference monitoring, and production cognitive-runtime experience. See [INSPIRATION.md](INSPIRATION.md) for the full provenance.

Sakshi is **not** a MIDCA implementation, MIDCA-compatible, or a fork of any MIDCA codebase. The MIDCA reference architecture is one influence among several.

## License

Apache-2.0. See [LICENSE](LICENSE).
