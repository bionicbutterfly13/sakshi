# Where Sakshi fits

A short, honest read on what Sakshi *is*, what it *isn't*, and which
problem it solves that adjacent tools don't. If you are picking
between Sakshi and a known agent framework, read this first.

## The one-paragraph version

Sakshi is a **metacognitive observation runtime** for Python agents.
It does not run the agent — it watches one you already have, through
typed seams, and gives that watching loop the structure that
production agents need: cycle traces, anomaly classification, write
gates, intervention auditing, goal-graph tracking. The pattern it
implements is called the *Witness*: a process that observes another
process without doing the work itself.

## Compared to LLM agent frameworks

LangGraph, AutoGen, smolagents, CrewAI, the Anthropic Agent SDK, and
similar libraries are **cognition frameworks**. They own how the
agent thinks: graph nodes, multi-agent conversations, role
hierarchies, planner/executor splits. You give them tools and a
prompt; they give you a working agent.

Sakshi is **not** a cognition framework. It does not:

- pick the next action;
- call any LLM;
- own tools, memory, or conversation history;
- generate plans;
- decide what goals to pursue.

What it does is sit beside the cognition loop you've already built
(in LangGraph, smolagents, or hand-rolled) and observe each cycle
through five typed protocol seams (`EventBus`, `GoalStateStore`,
`BasinHook`, `WriteGuard`, `Clock`). When the cycle reports its
phase outputs, Sakshi catches a structured cycle trace; when a
metacognitive policy decides to intervene, that decision routes
through `InterventionExecutor.validate` and gets audited; when the
agent claims a goal is achieved, the defensive guards check for
exogenous evidence.

You can use Sakshi *alongside* LangGraph or AutoGen — they handle
the cognition; Sakshi handles the observation. The
`examples/llm_research_agent/` example uses the Anthropic SDK
directly for cognition and wires it through Sakshi for everything
else.

## Compared to "just write your own observation layer"

Most production agent teams eventually grow some version of this on
their own: a hand-rolled event bus, ad-hoc anomaly counters, a
`should_we_actually_publish_this_write()` helper. The cost of doing
it yourself is real:

- **Every host re-invents** the same shapes: cycle traces, phase
  results, intervention records, anomaly events.
- **Type contracts drift** between observer and observed. The
  observability layer rots out of sync with the cognition layer
  because nothing forces them to agree.
- **Audit trails are non-uniform.** Reviewing what an agent did six
  weeks ago means reading per-team log formats.

Sakshi imposes a small, typed contract on those shapes
(`PhaseResult`, `CycleTrace`, `InterventionRecord`, `GuardVerdict`,
`AnomalyEvent`) and ships defaults for the awkward parts —
`DenyByDefaultWriteGuard` so a half-finished safety wiring fails
closed, `EvidenceRequiringRewardIntegrityGuard` so an agent can't
silently claim "goal achieved" without evidence, a `PhaseRegistry`
that emits one canonical `sakshi.cycle.complete` event regardless of
which host is driving the cycle. The cost of buying these from
Sakshi is one optional dependency and ~120 µs per cycle (see
[performance](performance.md)).

## What you get when you pick this up

The STABLE surface (see [1.0 stability](1.0-stability.md)) is the
minimum any host needs:

- **Protocols** (`EventBus`, `GoalStateStore`, `BasinHook`,
  `WriteGuard`, `Clock`) — the five seam points. Implement these
  against your bus, store, and safety policy.
- **Cycle infrastructure** — `PhaseRegistry` drives the cycle and
  emits the canonical complete event; `LastNPruner`,
  `SinceAnomalyPruner`, and `WhereExpectationFiredPruner` trim trace
  history.
- **Intervention auditing** — `InterventionExecutor` gates every
  meta-control action through a host-supplied
  `InterventionPermissionPolicy`, with a bounded ring of
  `InterventionRecord`s as the audit history.
- **Defensive guards** — `RewardIntegrityGuard`,
  `ModificationIntegrityGuard`, and their default implementations
  refuse suspicious goal-achievement claims and integrity-critical
  constraint demotions.
- **Goal lifecycle** — `Goal`, `GoalEvent`, `GoalMode` plus a
  `GoalGraph` for hierarchical decomposition.

The PROVISIONAL surface (calibration, motivation, trust, uncertainty
typing, TRAP failure classification, anticipatory risk) ships
working today but is more likely to gain deprecation warnings before
1.0 if real-world usage surfaces a better shape.

## When you should *not* pick this up

- **You don't have an agent yet.** Build the cognition first (with
  LangGraph, smolagents, raw `anthropic` SDK, whatever). Sakshi
  becomes useful once you have *something to watch*.
- **You don't need an audit trail.** If the agent is a
  one-shot chat completion with no persistent goals and no
  safety-relevant writes, Sakshi is overkill.
- **You want batteries-included.** Sakshi gives you the seams and the
  default policies. The host still wires the bus, the persistence
  store, and the production safety policy. Quickstart defaults
  (`NoOpEventBus`, `AlwaysPermitWriteGuard`) are *intentionally
  inert* — they preserve cycle behavior in tests but are not safe in
  production. See `DenyByDefaultPolicy` and `DenyByDefaultWriteGuard`
  for the fail-closed alternatives.

## The shorter version

> If the agent ecosystem were a stack, LangGraph and friends are
> the cognition layer. Sakshi is the layer that records what the
> cognition layer did, why, and whether anyone should trust it. It
> is not your agent; it is the witness sitting next to your agent.
