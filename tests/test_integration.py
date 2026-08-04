"""End-to-end test of fetch -> compute -> report, with GitHub's HTTP API
mocked out. (This sandbox's network doesn't reach api.github.com, so this
mock-based integration test is what actually exercises the full pipeline
here; `refresh-report.yml` runs the real thing against live data once this
is pushed to GitHub Actions, which has open internet access.)
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dx_dashboard.report import build_report

PRS_PAGE_1 = [
    {
        "number": 101,
        "title": "feat: add retry logic",
        "body": "Closes #90\n\nCo-authored-by: Claude <noreply@anthropic.com>",
        "created_at": "2026-06-01T10:00:00Z",
        "merged_at": "2026-06-01T14:00:00Z",
        "labels": [],
        "html_url": "https://github.com/example/repo/pull/101",
    },
    {
        "number": 100,
        "title": "fix: null pointer on empty config",
        "body": "Fixes #88",
        "created_at": "2026-05-28T09:00:00Z",
        "merged_at": "2026-05-30T09:00:00Z",
        "labels": [],
        "html_url": "https://github.com/example/repo/pull/100",
    },
    {
        "number": 99,
        "title": 'Revert "feat: add retry logic"',
        "body": "",
        "created_at": "2026-05-25T09:00:00Z",
        "merged_at": "2026-05-25T11:00:00Z",
        "labels": [],
        "html_url": "https://github.com/example/repo/pull/99",
    },
]

RUNS = {
    "workflow_runs": [
        {"created_at": "2026-06-01T15:00:00Z", "status": "completed", "conclusion": "success", "head_branch": "main"},
        {"created_at": "2026-05-30T10:00:00Z", "status": "completed", "conclusion": "success", "head_branch": "main"},
        {"created_at": "2026-05-25T12:00:00Z", "status": "completed", "conclusion": "failure", "head_branch": "main"},
    ]
}

ISSUES_PAGE_1 = [
    {
        "created_at": "2026-05-24T08:00:00Z",
        "closed_at": "2026-05-25T09:00:00Z",
        "labels": [{"name": "bug"}],
    }
]


def fake_get(self, path, params=None):
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = lambda: None
    params = params or {}
    if path.endswith("/pulls"):
        resp.json.return_value = PRS_PAGE_1 if params.get("page", 1) == 1 else []
    elif path.endswith("/actions/runs"):
        resp.json.return_value = RUNS if params.get("page", 1) == 1 else {"workflow_runs": []}
    elif path.endswith("/issues"):
        resp.json.return_value = ISSUES_PAGE_1 if params.get("page", 1) == 1 else []
    else:
        resp.json.return_value = []
    return resp


@patch("dx_dashboard.github_client.GitHubClient._get", new=fake_get)
def test_build_report_end_to_end():
    report = build_report("example", "repo", pr_pages=2, run_pages=2, issue_pages=2)

    assert report["repo"] == "example/repo"
    assert report["dora"]["sample_size"]["merged_prs"] == 3
    assert report["dora"]["change_failure_rate_pct"] is not None
    assert report["core4"]["quality"]["revert_rate_pct"] > 0
    assert report["ai_impact"]["ai_assisted_pr_count"] == 1
    assert len(report["recent_prs"]) == 3
