"""Fail-closed publishing authorization shared by the orchestrator and publisher."""

from __future__ import annotations


def _enabled(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def publishing_allowed(test_mode: object, publish_enabled: object) -> bool:
    """Publishing requires BOTH an explicit enable flag and test mode OFF."""
    return _enabled(publish_enabled) and not _enabled(test_mode)
