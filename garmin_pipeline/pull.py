"""Activity retrieval and planned-vs-actual analysis (Phase 2 stub)."""

from __future__ import annotations

from typing import Any


def pull_activities(
    date_from: str,
    date_to: str,
) -> list[dict[str, Any]]:
    """Fetch completed activities for a date range.

    Phase 2: Not yet implemented.
    """
    raise NotImplementedError("Activity pull is planned for Phase 2.")


def diff_planned_vs_actual(
    planned: dict[str, Any],
    actual: dict[str, Any],
) -> dict[str, Any]:
    """Compare a planned workout against a completed activity.

    Phase 2: Not yet implemented.
    """
    raise NotImplementedError("Planned-vs-actual diff is planned for Phase 2.")
