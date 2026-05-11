# llm_research_agent — LLM cognition wrapped by Sakshi

The bigger sibling of `toy_blocks_agent`. The host's cognition here is
an actual language model — Anthropic Claude in the live demo —
decomposing a research question, answering each subgoal, recovering
from low-confidence answers, and synthesizing a final report.
Sakshi observes every step through its standard seams.

## What it shows on top of `toy_blocks_agent`

- A real `LLMClient` protocol so the example can run with a
  deterministic `MockLLMClient` (tests, offline demos) or the
  Anthropic SDK (`AnthropicLLMClient`, with prompt caching wired).
- A `GoalGraph` populated dynamically: one root goal per research
  question, N child goals from the LLM's decomposition. Each subgoal
  is `mark_achieved` or `mark_abandoned` based on the answer's
  confidence.
- A typed anomaly path: low-confidence answers fire
  `AnomalyKind.LOW_CONFIDENCE` on the event bus, the agent reframes
  the question and re-queries the LLM once, and the trace records
  both the anomaly and the recovery.
- The publish step routes through `WriteGuard.check`, so a host
  wiring a real safety policy can veto the published research output.

## Run

Mock client (no API key, no network):

```bash
pip install -e .
python -m examples.llm_research_agent.main
```

Live Anthropic call:

```bash
pip install -e .[llm-examples]
export ANTHROPIC_API_KEY=sk-ant-...
python -m examples.llm_research_agent.main --live
```

Expected output (mock mode):

```
=== research transcript ===
question: How should a small Python library decide when to commit to a 1.0 release?
subgoals: 3
  - research-sub-01: confidence=0.85
  - research-sub-02: confidence=0.75 [anomaly=low_confidence, reframed=True]
  - research-sub-03: confidence=0.90

--- synthesis ---
A small Python library should commit to 1.0 only when ...

published: True
sakshi cycle.complete events: 5
research anomalies observed: 1
```

## Files

| File | Role |
|------|------|
| `llm_client.py` | The minimal `LLMClient` protocol plus the Anthropic SDK adapter (with prompt caching) and the deterministic `MockLLMClient` used by tests. |
| `agent.py` | `ResearchAgent` — decompose → answer-per-subgoal → synthesize, with a one-shot reframe on low-confidence answers. |
| `adapters.py` | Three reference Sakshi seam adapters (event bus, write guard, optional state store). |
| `main.py` | CLI runner. `--live` flips between the mock and the Anthropic client. |

## Extending

Swap in your real LLM client by writing a class that satisfies
`LLMClient`. The agent depends on the protocol, not on the Anthropic
SDK — point it at a local model, a different vendor SDK, or a
rate-limited cached layer in front of either.
