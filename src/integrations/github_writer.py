"""Write-side GitHub client: list and create issues, scoped to a single label."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

GITHUB_API = "https://api.github.com"
USER_AGENT = "github-logs/0.1"
AUTO_LABEL = "github-logs/auto"


class GitHubWriter:
    def __init__(self, token: str, timeout: float = 20.0) -> None:
        self._client = httpx.Client(
            base_url=GITHUB_API,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "User-Agent": USER_AGENT,
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> GitHubWriter:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def is_private(self, owner: str, repo: str) -> bool:
        """Returns True if the repo is private. Defaults to True on errors so
        we fail closed (don't accidentally write to public repos)."""
        resp = self._client.get(f"/repos/{owner}/{repo}")
        if resp.status_code != 200:
            return True
        return bool(resp.json().get("private", False))

    def existing_open_titles(self, owner: str, repo: str) -> set[str]:
        """Titles of open issues with the auto-generated label.

        Used to skip duplicate creates when a previous run already opened
        an issue with the same title for this repo.
        """
        titles: set[str] = set()
        for issue in self._iter_issues(owner, repo, state="open", labels=AUTO_LABEL):
            if "pull_request" in issue:
                continue
            titles.add(issue["title"])
        return titles

    def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        labels: list[str],
    ) -> int:
        resp = self._client.post(
            f"/repos/{owner}/{repo}/issues",
            json={"title": title, "body": body, "labels": labels},
        )
        resp.raise_for_status()
        return int(resp.json()["number"])

    def _iter_issues(
        self,
        owner: str,
        repo: str,
        state: str,
        labels: str,
    ) -> Iterator[dict[str, Any]]:
        url: str | None = f"/repos/{owner}/{repo}/issues"
        params: dict[str, Any] | None = {
            "state": state,
            "labels": labels,
            "per_page": 100,
        }
        while url:
            resp = self._client.get(url, params=params)
            params = None
            if resp.status_code == 404:
                return
            resp.raise_for_status()
            yield from resp.json()
            url = _next_link(resp.headers.get("Link"))


def _next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip()
        if section.endswith('rel="next"'):
            return section.split(";", 1)[0].strip().strip("<>")
    return None
