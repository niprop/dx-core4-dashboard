"""Orchestrates a full analysis run: fetch -> compute -> JSON report."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .ai_detection import ai_impact_summary
from .github_client import GitHubClient
from .metrics import core4_scores, dora_metrics


def build_report(
    owner: str,
    repo: str,
    token: str | None = None,
    pr_pages: int = 5,
    run_pages: int = 3,
    issue_pages: int = 3,
) -> dict[str, Any]:
    client = GitHubClient(token=token)

    prs = client.pull_requests(owner, repo, state="closed", max_pages=pr_pages)
    runs = client.workflow_runs(owner, repo, max_pages=run_pages)
    incidents = client.issues(owner, repo, state="closed", labels="bug", max_pages=issue_pages)

    dora = dora_metrics(prs, runs, incidents)
    core4 = core4_scores(prs, runs, dora)
    ai = ai_impact_summary(prs)

    return {
        "repo": f"{owner}/{repo}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "methodology": (
            "DORA four keys + a DX Core 4-inspired Speed/Effectiveness/Quality/Impact "
            "breakdown, computed from public GitHub PR, Actions, and Issues data. "
            "Independent, unaffiliated reimplementation for portfolio/demo purposes."
        ),
        "dora": dora,
        "core4": core4,
        "ai_impact": ai,
        "recent_prs": [
            {
                "number": p.get("number"),
                "title": p.get("title"),
                "merged_at": p.get("merged_at"),
                "created_at": p.get("created_at"),
                "html_url": p.get("html_url"),
            }
            for p in prs
            if p.get("merged_at")
        ][:15],
    }
