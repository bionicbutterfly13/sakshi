# Inspirations

> Sakshi is a metacognitive runtime inspired in part by MIDCA's distinction between object-level cognition and metacognitive monitoring/control. It is not affiliated with MIDCA and is not a drop-in implementation of the MIDCA reference architecture.

Listed alphabetically; no implicit ranking by listing order.

## Active Inference (Friston et al.)

Active Inference influenced Sakshi's use of expectation, surprise, and
performance proxies during the ASSESS step. Sakshi does not implement a full
active-inference stack; host applications may supply richer inference services
through protocols and adapters.

## ACT-R (Anderson et al.)

ACT-R influenced the distinction between procedural traces and runtime control
signals. ACT-R bridges live downstream in host applications, not in Sakshi, so
the package core remains independent of ACT-R runtimes.

## CLARION (Sun)

CLARION's distinction between implicit drives and explicit goals
informed the shape of Sakshi's `MotivationType` taxonomy and
`MotivationAuditor`. Sakshi does not implement CLARION's two-level
neural substrate; the host owns its own motivation system and emits
typed `MotivationEvent` records that Sakshi observes.

## Foundations of Trusted Autonomy (Abbass, Scholz, Reid eds., 2018, Springer Open)

Several Phase D / E / F primitives draw shape from chapters in this
volume: Devitt's competence-vs-integrity bifurcation
(`TrustBifurcation`), Smithson's three-mode uncertainty taxonomy
(`UncertaintyType`), Hart et al.'s communicative-cue framing
(`TrustReport`), Scholz's confusion-objective error shaping
(`ConfusionWeighter`), Merrick's six-class motivation taxonomy
(`MotivationType`), Bringsjord's creativity-trust caveat
(`CreativityEnvelope`), and Hutter's failure-mode taxonomy
(`RewardIntegrityGuard`, `ModificationIntegrityGuard`,
`KnowledgeRewardBalance`). Sakshi is not a derivative work of any
chapter; the influence is on shape and naming of the typed surface
the package exposes.

## Goal Lifecycle Networks (Roberts, NRL)

Roberts's goal-lifecycle work informed the `GoalMode` state machine
and the `GoalOperation` taxonomy. Sakshi adopts the lifecycle vocabulary
but does not reproduce ActorSim's runtime.

## MIDCA (Cox, Alavi, Dannenhauer, et al.)

MIDCA influenced Sakshi's object-level versus metacognitive distinction and the
general idea of monitoring cognition before selecting control actions. Sakshi is
not affiliated with MIDCA, is not a drop-in implementation of the MIDCA
reference architecture, and shares zero code with the MIDCA codebase.

## Production cognitive-runtime experience

Sakshi was extracted from production-runtime experience after the core
metacognitive pieces were separated from host-specific services such as event
buses, graph stores, attractor basins, and active-inference adapters.

## Sandved-Smith et al. (niab018)

Opacity and meta-awareness concepts influenced Sakshi's attention to monitoring
when a cognitive process is becoming difficult for the host to inspect or steer.
Concrete opacity bridges remain host adapters rather than package-core
dependencies.
