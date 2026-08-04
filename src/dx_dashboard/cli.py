"""CLI: python -m dx_dashboard.cli --owner OWNER --repo REPO [--out PATH]"""

from __future__ import annotations

import argparse
import json
import sys

from .report import build_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a DORA / Core4-style report for a GitHub repo.")
    parser.add_argument("--owner", required=True, help="GitHub org or user, e.g. 'pallets'")
    parser.add_argument("--repo", required=True, help="Repo name, e.g. 'click'")
    parser.add_argument("--token", default=None, help="GitHub token (else reads GITHUB_TOKEN env var)")
    parser.add_argument("--out", default="data/report.json", help="Output JSON path")
    parser.add_argument("--pr-pages", type=int, default=5)
    parser.add_argument("--run-pages", type=int, default=3)
    parser.add_argument("--issue-pages", type=int, default=3)
    args = parser.parse_args(argv)

    report = build_report(
        args.owner,
        args.repo,
        token=args.token,
        pr_pages=args.pr_pages,
        run_pages=args.run_pages,
        issue_pages=args.issue_pages,
    )

    with open(args.out, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Wrote {args.out} for {args.owner}/{args.repo}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
