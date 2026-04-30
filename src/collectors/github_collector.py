"""GitHub REST client with pagination and rate-limit awareness."""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

import httpx

GITHUB_API = "https://api.github.com"
USER_AGENT = "github-logs/0.1"


class GitHubClient:
    def __init__(self, token: str, username: str, timeout: float = 20.0) -> None:
        self._username = username
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

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # -- public API -------------------------------------------------------

    def list_repos(self) -> list[dict[str, Any]]:
        """Public + private repos owned by the user (excludes archived)."""
        repos = list(
            self._paginate(
                "/user/repos",
                params={"per_page": 100, "affiliation": "owner", "sort": "updated"},
            )
        )
        return [r for r in repos if not r.get("archived")]

    def list_commits(self, owner: str, repo: str, since_iso: str) -> list[dict[str, Any]]:
        return list(
            self._paginate(
                f"/repos/{owner}/{repo}/commits",
                params={"author": self._username, "since": since_iso, "per_page": 100},
                allow_404_or_409=True,
            )
        )

    def get_commit(self, owner: str, repo: str, sha: str) -> dict[str, Any]:
        resp = self._request("GET", f"/repos/{owner}/{repo}/commits/{sha}")
        return resp.json()

    def list_issues(self, owner: str, repo: str, since_iso: str) -> list[dict[str, Any]]:
        items = list(
            self._paginate(
                f"/repos/{owner}/{repo}/issues",
                params={"since": since_iso, "state": "all", "per_page": 100},
                allow_404_or_409=True,
            )
        )
        # GitHub's /issues endpoint returns PRs too; filter them out.
        return [i for i in items if "pull_request" not in i]

    # -- internals --------------------------------------------------------

    def _paginate(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        allow_404_or_409: bool = False,
    ) -> Iterator[dict[str, Any]]:
        url: str | None = path
        first = True
        while url:
            resp = self._request(
                "GET",
                url,
                params=params if first else None,
                allow_404_or_409=allow_404_or_409,
            )
            first = False
            if resp is None:
                return
            data = resp.json()
            if isinstance(data, list):
                yield from data
            else:
                yield data
                return
            url = _next_link(resp.headers.get("Link"))

    def _request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        allow_404_or_409: bool = False,
    ) -> httpx.Response | None:
        for _ in range(3):
            resp = self._client.request(method, url, params=params)
            if resp.status_code == 200:
                return resp
            if allow_404_or_409 and resp.status_code in (404, 409):
                # 409 = empty repo, 404 = vanished/permission gone; skip.
                return None
            if resp.status_code == 403 and _is_rate_limited(resp):
                _sleep_until_reset(resp)
                continue
            resp.raise_for_status()
        raise RuntimeError(f"exhausted retries for {method} {url}")


def _next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip()
        if section.endswith('rel="next"'):
            url = section.split(";", 1)[0].strip()
            return url.strip("<>")
    return None


def _is_rate_limited(resp: httpx.Response) -> bool:
    return resp.headers.get("X-RateLimit-Remaining") == "0"


def _sleep_until_reset(resp: httpx.Response) -> None:
    reset = resp.headers.get("X-RateLimit-Reset")
    if not reset:
        time.sleep(30)
        return
    wait = max(0, int(reset) - int(time.time())) + 1
    time.sleep(min(wait, 900))
