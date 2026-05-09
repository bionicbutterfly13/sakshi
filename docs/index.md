# Sakshi

Sakshi is a typed metacognitive runtime for Python agents: the Witness pattern.
It observes agent execution through explicit host-supplied seams, evaluates
runtime traces against expectations, and emits signals a host can route to
dashboards, gates, audits, or meta-control policies.

## Start Here

- [Architecture](architecture.md) explains the package layers and host boundary.
- [Principles](principles.md) records non-negotiable design and identity rules.
- [Quality](quality.md) tracks implementation status by package area.
- [API Reference](api/index.md) is generated from the typed Python package.

## Install

```bash
pip install pysakshi
```

```python
import sakshi
```

## Production Boundary

The default no-op and always-permit helpers are intentionally inert for tests
and examples. Production hosts must inject concrete implementations of the
public protocols before relying on emitted events, world-state lookups, or write
guards.
