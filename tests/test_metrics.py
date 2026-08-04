import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dx_dashboard.ai_detection import ai_impact_summary, is_ai_assisted
from dx_dashboard.metrics import core4_scores, dora_metrics


def pr(number, created, merged=None, title="fix: thing", body=""):
    return {
        "number": number,
        "title": title,
        "body": body,
        "created_at": created,
        "merged_at": merged,
        "labels": [],
    }


def run(created, status="completed", conclusion="success", branch="main"):
    return {"created_at": created, "status": status, "conclusion": conclusion, "head_branch": branch}


def test_lead_time_uses_median_of_merged_prs():
    prs = [
        pr(1, "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"),  # 24h
        pr(2, "2026-01-01T00:00:00Z", "2026-01-05T00:00:00Z"),  # 96h
        pr(3, "2026-01-01T00:00:00Z", None),  # unmerged, ignored
    ]
    dora = dora_metrics(prs, [], [])
    assert dora["lead_time_for_changes_hours"] == 60.0
    assert dora["sample_size"]["merged_prs"] == 2


def test_change_failure_rate_only_counts_completed_default_branch_runs():
    runs = [
        run("2026-01-01T00:00:00Z", conclusion="success"),
        run("2026-01-02T00:00:00Z", conclusion="failure"),
        run("2026-01-03T00:00:00Z", status="in_progress", conclusion=None),
        run("2026-01-04T00:00:00Z", conclusion="success", branch="feature-x"),
    ]
    dora = dora_metrics([], runs, [])
    # 2 completed on main (1 success, 1 failure) -> 50% failure rate
    assert dora["change_failure_rate_pct"] == 50.0
    assert dora["sample_size"]["completed_workflow_runs"] == 2


def test_mttr_from_incident_labeled_issues():
    incidents = [
        {"created_at": "2026-01-01T00:00:00Z", "closed_at": "2026-01-01T02:00:00Z"},  # 2h
        {"created_at": "2026-01-01T00:00:00Z", "closed_at": "2026-01-01T06:00:00Z"},  # 6h
    ]
    dora = dora_metrics([], [], incidents)
    assert dora["mttr_hours"] == 4.0


def test_core4_revert_rate_and_impact_link_rate():
    prs = [
        pr(1, "2026-01-01T00:00:00Z", "2026-01-01T04:00:00Z", title="feat: add thing", body="Closes #12"),
        pr(2, "2026-01-01T00:00:00Z", "2026-01-01T08:00:00Z", title="Revert \"feat: add thing\"", body=""),
    ]
    dora = dora_metrics(prs, [], [])
    core4 = core4_scores(prs, [], dora)
    assert core4["quality"]["revert_rate_pct"] == 50.0
    assert core4["impact"]["pct_prs_linked_to_issue"] == 50.0


def test_is_ai_assisted_matches_known_signals():
    assert is_ai_assisted(pr(1, "2026-01-01T00:00:00Z", title="feat: x", body="Co-authored-by: Claude <noreply@anthropic.com>"))
    assert is_ai_assisted({"title": "x", "body": "", "labels": [{"name": "ai-assisted"}]})
    assert not is_ai_assisted(pr(1, "2026-01-01T00:00:00Z", title="fix: bug", body="manual fix, no ai"))


def test_ai_impact_summary_splits_and_compares_cycle_time():
    prs = [
        pr(1, "2026-01-01T00:00:00Z", "2026-01-01T02:00:00Z", body="Co-authored-by: Claude"),  # 2h, AI
        pr(2, "2026-01-01T00:00:00Z", "2026-01-01T10:00:00Z", body=""),  # 10h, non-AI
    ]
    summary = ai_impact_summary(prs)
    assert summary["ai_assisted_pr_count"] == 1
    assert summary["non_ai_pr_count"] == 1
    assert summary["median_cycle_time_hours_ai_assisted"] == 2.0
    assert summary["median_cycle_time_hours_non_ai"] == 10.0
    assert summary["cycle_time_delta_pct"] == -80.0
