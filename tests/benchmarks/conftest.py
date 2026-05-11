"""Configuration for the benchmark suite.

Benchmarks run a small number of high-signal hot paths through Sakshi
and persist results to ``.benchmarks/`` so future runs can compare
against a saved baseline. They are intentionally separated from the
unit-test suite — ``make test`` and the coverage gate do not pick them
up, only ``make benchmark`` does.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session", autouse=True)
def _set_asyncio_default_loop_scope() -> None:
    """Match the unit suite's asyncio_mode=auto behavior."""
    return None
