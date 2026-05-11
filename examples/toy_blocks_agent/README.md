# toy_blocks_agent — Sakshi reference integration

A self-contained host that wires its own cognition through Sakshi's
Witness seams. No LLM, no network, no persistence backend — only stdlib
plus Sakshi. Read it as the smallest answer to "how do I plug Sakshi
into an existing agent?"

## What it shows

- A real **host** (`agent.py`) that owns its planner, world model, and
  action executor. Sakshi never plans or acts on its behalf.
- Three real protocol adapters (`adapters.py`):
  - `InMemoryEventBus` → `sakshi.protocols.EventBus`
  - `InMemoryGoalStateStore` → `sakshi.protocols.GoalStateStore`
  - `LoggingWriteGuard` → `sakshi.protocols.WriteGuard`
- A `PhaseRegistry` recording each PERCEIVE / PLAN / ACT cycle, emitting
  `sakshi.cycle.complete` to the bus, and a `WriteGuard.check` firing
  for every executed action — the typed audit surface a production host
  would route through its own observability layer.

## What it does

The agent stacks three blocks (A on B on C) starting from a flat
table. A greedy planner emits one move per cycle until the goal stack
is reached. The harness asks Sakshi to observe each cycle and stores
the post-action world state through the `GoalStateStore` adapter.

## Run

From the repo root:

```bash
pip install -e .
python -m examples.toy_blocks_agent.main
```

Expected output (4 cycles to reach the goal):

```
=== agent cycle transcript ===
  toy-001: action=pickup(B) status=ok
  toy-002: action=putdown(B, C) status=ok
  toy-003: action=pickup(A) status=ok
  toy-004: action=putdown(A, B) status=ok

final world.on: {'ON(C,table)': 'true', 'ON(B,C)': 'true', 'ON(A,B)': 'true'}
sakshi cycle.complete events emitted: 4
```

## Files

| File | Role |
|------|------|
| `world.py` | The toy domain. Blocks-world state plus two action DTOs and an `apply()` step function. |
| `agent.py` | The host's cognition: a 3-phase PERCEIVE → PLAN → ACT loop with a greedy planner. |
| `adapters.py` | The three reference protocol adapters. Replace these with your host's real bus / store / safety policy. |
| `main.py` | The wiring: builds the `PhaseRegistry`, runs cycles, prints the transcript. |

## Extending

Plug your own host in by keeping the seam contracts:

1. Replace `BlocksAgent` with your real cognition loop.
2. Replace `BlocksWorld` with your real environment (or remove if your
   host has no world model of its own).
3. Swap `InMemoryEventBus` for an adapter around your bus
   (Kafka, Redis, in-process pub/sub, whatever).
4. Swap `InMemoryGoalStateStore` for your persistence (Neo4j, Postgres,
   vector store, …).
5. Swap `LoggingWriteGuard` for the deny-or-permit policy you want
   in front of agent-originated writes — start from
   `sakshi.protocols.DenyByDefaultWriteGuard` if you want the safest
   scaffold.

The Sakshi side does not change.
