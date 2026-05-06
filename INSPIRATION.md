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
