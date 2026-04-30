"""Sakshi runtime configuration.

`SakshiConfig` holds the flags and thresholds that the framework
modules currently read from a host's settings layer. Hosts construct
one `SakshiConfig` per Sakshi runtime instance and pass it explicitly
to constructors. Sakshi never reads global configuration state.

This is a skeleton. Concrete fields land alongside the modules that
consume them as later phases port each module behind the seam.
"""

from __future__ import annotations

from pydantic import BaseModel


class SakshiConfig(BaseModel):
    """Top-level configuration object passed to Sakshi runtime classes.

    Defaults preserve current production behavior. Specific fields are
    populated as later phases port each module.
    """

    model_config = {"frozen": True, "extra": "forbid"}


__all__ = ["SakshiConfig"]
