# Recovery

Create and retain a `StrategyHinter` when recovery attempts should escalate
across calls. The convenience functions are stateless when no hinter is passed.
Each hinter retains state for at most 1,024 tasks by default; hosts can select a
different positive bound and should call `reset_attempts()` when a task closes.

::: sakshi.recovery
