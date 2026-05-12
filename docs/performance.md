# Performance baseline

Sakshi adds a small, fixed amount of overhead to a host's cognitive
loop. This page records the measured baselines for the hot paths so
future runs can detect regressions.

## How to run

```bash
make benchmark
```

Behind the scenes that runs `pytest tests/benchmarks
--benchmark-only`. Each run prints min / median / mean / standard
deviation per benchmark and writes a per-machine JSON to
`.benchmarks/` (gitignored — runs are reproducible, not stored). To
compare against a saved snapshot:

```bash
pytest tests/benchmarks --benchmark-only --benchmark-save=local
pytest tests/benchmarks --benchmark-only --benchmark-compare=local
```

## 0.12.0 baseline

Measured on macOS, Python 3.11, in-process (no IO). Numbers are
**median per call**. The set is intentionally small — these are the
operations a host repeatedly hits inside a real cognitive cycle, so
they're the ones worth gating against regression.

| Hot path | Median | What it covers |
|---|---|---|
| `InterventionExecutor.validate` | ~21 µs | Cooldown lookup + policy call + audit append on one `ControlAction`. |
| `CognitiveBlackboard` set + get | ~58 µs | Async round trip on a per-key lock. |
| `PhaseRegistry` full cycle | ~120 µs | `start_cycle` → 6 phase outputs → `finalize_cycle` (emits `sakshi.cycle.complete`). |
| `CognitiveBlackboard.snapshot` (100 keys) | ~175 µs | Per-key lock acquisition + deepcopy of a non-trivial payload. |
| `GoalGraph.get_active_frontier` (500 goals) | ~310 µs | Frontier walk on a wide goal graph. |
| `toy_blocks_agent` end-to-end (4 cycles) | ~345 µs | Full integration: Sakshi seam overhead + a real host loop reaching its goal. |
| `GoalGraph.add_goal` chain (50 deep) | ~545 µs | Adding a 50-deep parent→child chain. |

## In context

The numbers above are micro-benchmarks. Reading them on their own is
hard — is 120 µs per cycle "fast"? It depends on what else the agent
is doing. The honest framing:

| Operation | Typical latency | Sakshi cycle as % of this |
|---|---|---|
| Claude Opus call (uncached, 500 tokens out) | 1.5–4.0 s | ~0.003% |
| Claude Sonnet call (uncached, 500 tokens out) | 0.5–1.5 s | ~0.01% |
| Claude Haiku call (uncached, 500 tokens out) | 0.15–0.4 s | ~0.05% |
| Prompt-cache hit (first token) | <0.1 s | ~0.12% |
| HTTP tool call (round trip, same region) | 50–200 ms | ~0.1% |
| Local Postgres read | 1–20 ms | ~1% |
| Local filesystem read (cached) | 0.05–0.5 ms | ~30–200% |
| **Sakshi full cycle** | **0.12 ms** | — |
| Sakshi intervention validate | 0.02 ms | — |

What this says:

- For any agent whose cognition includes **at least one LLM call per
  cycle**, Sakshi's overhead is in the noise floor. The agent's
  wall-clock dominated by the model.
- For agents whose cycle is **only** Python (e.g., a rule-based
  controller, the `toy_blocks_agent` example), Sakshi is the
  expensive part — but the absolute cost is still ~0.1 ms, which is
  the same magnitude as a single filesystem read. A real loop will
  trivially run thousands of cycles per second.
- The intervention validate path (~21 µs) is the fastest seam. If
  your meta-loop fires interventions on every cycle, the audit
  layer is not what slows you down.

## Read this as

- A typical Sakshi cycle costs roughly **0.1 ms** end-to-end. Hosts
  with millisecond-scale agents pay <1% overhead; hosts running
  LLM-dominated cycles pay rounding error.
- Hot paths that touch async locks (blackboard, snapshot) are
  10–100× faster than the full cycle, so swapping them under load is
  not a bottleneck.
- The goal-graph operations scale linearly in goal count; planning
  ahead, a host pushing thousands of goals per second should batch
  rather than call `add_goal` once per leaf.

If `make benchmark` shows a regression of more than ~30% on any of
these for a non-feature commit, treat it as a bug.
