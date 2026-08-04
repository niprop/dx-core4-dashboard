"""DORA and DX Core 4-style metric calculations.

This is an independent, open-source reimplementation inspired by public
research (the DORA four keys, and DX's published Core 4 framework: Speed,
Effectiveness, Quality, Impact). It is not affiliated with or endorsed by
DORA, Google, DX, or Atlassian -- it exists to demonstrate the methodology
against real GitHub data.

All timestamps in/out are ISO 8601 strings (GitHub's native format) or None.
"""

from __future__ import annotations

import statistics
from datetime import datetime, timezone
from typing import Any


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _hours_between(a: str | None, b: str | None) -> float | None:
    da, db = _parse(a), _parse(b)
    if da is None or db is None:
        return None
    return (db - da).total_seconds() / 3600.0


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def _rating(value: float | None, thresholds: tuple[float, float, float], lower_is_better: bool = True) -> str:
    """Bucket a value into Elite/High/Medium/Low given (elite, high, medium) cutoffs."""
    if value is None:
        return "unknown"
    elite, high, medium = thresholds
    cmp = (lambda v, t: v <= t) if lower_is_better else (lambda v, t: v >= t)
    if cmp(value, elite):
        return "Elite"
    if cmp(value, high):
        return "High"
    if cmp(value, medium):
        return "Medium"
    return "Low"


def merged_prs(prs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [p for p in prs if p.get("merged_at")]


def dora_metrics(
    prs: list[dict[str, Any]], workflow_runs: list[dict[str, Any]], incidents: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compute the four DORA keys from PRs (lead time), workflow runs
    (deployment frequency + change failure rate), and incident-labeled
    issues (MTTR)."""
    merged = merged_prs(prs)

    lead_times = [
        h for p in merged
        if (h := _hours_between(p.get("created_at"), p.get("merged_at"))) is not None
    ]
    lead_time_hours = _median(lead_times)

    default_branch_runs = [r for r in workflow_runs if r.get("head_branch") in ("main", "master")]
    completed = [r for r in default_branch_runs if r.get("status") == "completed"]
    successful = [r for r in completed if r.get("conclusion") == "success"]
    failed = [r for r in completed if r.get("conclusion") == "failure"]

    weeks_covered = _weeks_span([r.get("created_at") for r in completed])
    deploys_per_week = (len(successful) / weeks_covered) if weeks_covered else None

    change_failure_rate = (len(failed) / len(completed)) if completed else None

    mttr_hours = _median([
        h for i in incidents
        if (h := _hours_between(i.get("created_at"), i.get("closed_at"))) is not None
    ])

    return {
        "lead_time_for_changes_hours": lead_time_hours,
        "lead_time_rating": _rating(lead_time_hours, (24, 24 * 7, 24 * 30)),
        "deployment_frequency_per_week": deploys_per_week,
        "deployment_frequency_rating": _rating(
            deploys_per_week, (7, 1, 1 / 4), lower_is_better=False
        ),
        "change_failure_rate_pct": None if change_failure_rate is None else round(change_failure_rate * 100, 1),
        "change_failure_rate_rating": _rating(change_failure_rate, (0.15, 0.30, 0.45)),
        "mttr_hours": mttr_hours,
        "mttr_rating": _rating(mttr_hours, (1, 24, 24 * 7)),
        "sample_size": {
            "merged_prs": len(merged),
            "completed_workflow_runs": len(completed),
            "incidents": len(incidents),
        },
    }


def _weeks_span(timestamps: list[str | None]) -> float | None:
    parsed = [t for t in (_parse(ts) for ts in timestamps) if t is not None]
    if len(parsed) < 2:
        return None
    span_days = (max(parsed) - min(parsed)).total_seconds() / 86400
    return max(span_days / 7, 1 / 7)  # floor at ~1 day to avoid divide-by-huge-number


def core4_scores(
    prs: list[dict[str, Any]], workflow_runs: list[dict[str, Any]], dora: dict[str, Any]
) -> dict[str, Any]:
    """A Core-4-flavored view of the same underlying data: Speed,
    Effectiveness, Quality, Impact. Speed/Quality lean on the DORA numbers
    already computed; Effectiveness and Impact are PR-review-shaped
    proxies since review/planning-tool data isn't available from the
    GitHub REST API alone."""
    merged = merged_prs(prs)

    cycle_times = [
        h for p in merged
        if (h := _hours_between(p.get("created_at"), p.get("merged_at"))) is not None
    ]
    throughput_per_week = None
    span = _weeks_span([p.get("merged_at") for p in merged])
    if span:
        throughput_per_week = len(merged) / span

    revert_count = sum(1 for p in merged if "revert" in (p.get("title") or "").lower())
    revert_rate = (revert_count / len(merged)) if merged else None

    impact_linked = sum(
        1 for p in merged
        if any(kw in (p.get("body") or "").lower() for kw in ("closes #", "fixes #", "resolves #"))
    )
    impact_link_rate = (impact_linked / len(merged)) if merged else None

    return {
        "speed": {
            "median_cycle_time_hours": _median(cycle_times),
            "pr_throughput_per_week": throughput_per_week,
        },
        "effectiveness": {
            "deployment_frequency_per_week": dora["deployment_frequency_per_week"],
        },
        "quality": {
            "change_failure_rate_pct": dora["change_failure_rate_pct"],
            "revert_rate_pct": None if revert_rate is None else round(revert_rate * 100, 1),
        },
        "impact": {
            "pct_prs_linked_to_issue": None if impact_link_rate is None else round(impact_link_rate * 100, 1),
            "note": "Proxy metric -- real Impact scoring needs planning-tool data (Jira/Linear), not just Git.",
        },
    }
