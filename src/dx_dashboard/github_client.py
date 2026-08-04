"""Thin GitHub REST API client for pulling the raw signals DORA / Core 4
metrics are built from: pull requests, workflow runs (deploy proxy), and
issues (incident proxy).

Only stdlib + requests. Works unauthenticated (60 req/hr) for small repos,
or with a GITHUB_TOKEN for anything bigger (5000 req/hr).
"""

from __future__ import annotations

import os
import time
from typing import Any, Iterator

import requests

API_ROOT = "https://api.github.com"


class GitHubClient:
    def __init__(self, token: str | None = None, timeout: int = 15):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.timeout = timeout
        self.session = requests.Session()
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self.session.headers.update(headers)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> requests.Response:
        url = path if path.startswith("http") else f"{API_ROOT}{path}"
        resp = self.session.get(url, params=params, timeout=self.timeout)
        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            reset = resp.headers.get("X-RateLimit-Reset")
            raise RuntimeError(
                f"GitHub API rate limit hit (resets at epoch {reset}). "
                "Set GITHUB_TOKEN to raise the limit."
            )
        resp.raise_for_status()
        return resp

    def _paginate(
        self, path: str, params: dict[str, Any] | None = None, max_pages: int = 5
    ) -> Iterator[dict[str, Any]]:
        params = dict(params or {})
        params.setdefault("per_page", 100)
        page = 1
        while page <= max_pages:
            params["page"] = page
            resp = self._get(path, params=params)
            batch = resp.json()
            if isinstance(batch, dict) and "items" in batch:
                batch = batch["items"]
            if not batch:
                return
            yield from batch
            if len(batch) < params["per_page"]:
                return
            page += 1
            time.sleep(0.05)  # be polite

    def pull_requests(
        self, owner: str, repo: str, state: str = "closed", max_pages: int = 5
    ) -> list[dict[str, Any]]:
        return list(
            self._paginate(
                f"/repos/{owner}/{repo}/pulls",
                params={"state": state, "sort": "updated", "direction": "desc"},
                max_pages=max_pages,
            )
        )

    def workflow_runs(self, owner: str, repo: str, max_pages: int = 3) -> list[dict[str, Any]]:
        runs: list[dict[str, Any]] = []
        params = {"per_page": 100}
        page = 1
        while page <= max_pages:
            params["page"] = page
            resp = self._get(f"/repos/{owner}/{repo}/actions/runs", params=params)
            batch = resp.json().get("workflow_runs", [])
            if not batch:
                break
            runs.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return runs

    def issues(
        self, owner: str, repo: str, state: str = "closed", labels: str | None = None, max_pages: int = 3
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"state": state}
        if labels:
            params["labels"] = labels
        items = list(self._paginate(f"/repos/{owner}/{repo}/issues", params=params, max_pages=max_pages))
        # GitHub's issues endpoint also returns PRs; filter those out.
        return [i for i in items if "pull_request" not in i]

    def pr_commits(self, owner: str, repo: str, pr_number: int) -> list[dict[str, Any]]:
        return list(self._paginate(f"/repos/{owner}/{repo}/pulls/{pr_number}/commits", max_pages=2))
