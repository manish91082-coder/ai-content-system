"""Fail-closed controls for external publishing.

Publishing requires BOTH an explicit enable flag and an explicitly disabled test mode.
Missing or malformed environment values always block external publishing.
"""
import os
from typing import Mapping, Optional

_TRUE = {"1", "true", "yes", "on"}

def publishing_is_enabled(env: Optional[Mapping[str, str]] = None) -> bool:
    values = os.environ if env is None else env
    enabled = str(values.get("PUBLISH_ENABLED", "")).strip().lower() in _TRUE
    test_mode = str(values.get("TEST_MODE", "true")).strip().lower() in _TRUE
    return enabled and not test_mode
