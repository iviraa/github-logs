"""Find and delete (or close) every issue tagged with the github-logs auto label.

Usage:
    cd github-logs
    source .venv/bin/activate

    # dry-run: list what would be deleted, do nothing
    GITHUB_TOKEN=ghp_xxx python -m scripts.cleanup_issues

    # actually delete (GraphQL deleteIssue, requires admin on the repo)
    GITHUB_TOKEN=ghp_xxx python -m scripts.cleanup_issues --delete

    # close instead of delete (REST, no admin needed)
    GITHUB_TOKEN=ghp_xxx python -m scripts.cleanup_issues --close
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from typing import Any

import httpx

GITHUB_API = "https://api.github.com"
GRAPHQL = "https://api.github.com/graphql"
LABEL = "github-logs/auto"


def list_owned_repos(client: httpx.Client) -> list[dict[str, Any]]:
    repos: list[dict[str, Any]] = []
    url: str | None = "/user/repos"
    params: dict[str, Any] | None = {"affiliation": "owner", "per_page": 100}
    while url:
        resp = client.get(url, params=params)
        params = None
        resp.raise_for_status()
        repos.extend(resp.json())
        url = _next_link(resp.headers.get("Link"))
    return repos


def list_auto_issues(
    client: httpx.Client, owner: str, repo: str
) -> Iterator[dict[str, Any]]:
    """All issues (open + closed) with the auto label, excluding pull requests."""
    url: str | None = f"/repos/{owner}/{repo}/issues"
    params: dict[str, Any] | None = {
        "state": "all",
        "labels": LABEL,
        "per_page": 100,
    }
    while url:
        resp = client.get(url, params=params)
        params = None
        if resp.status_code == 404:
            return
        resp.raise_for_status()
        for issue in resp.json():
            if "pull_request" in issue:
                continue
            yield issue
        url = _next_link(resp.headers.get("Link"))


def close_issue(client: httpx.Client, owner: str, repo: str, number: int) -> None:
    resp = client.patch(
        f"/repos/{owner}/{repo}/issues/{number}",
        json={"state": "closed", "state_reason": "not_planned"},
    )
    resp.raise_for_status()


def delete_issue(client: httpx.Client, node_id: str) -> None:
    resp = client.post(
        GRAPHQL,
        json={
            "query": "mutation($id:ID!){deleteIssue(input:{issueId:$id}){repository{id}}}",
            "variables": {"id": node_id},
        },
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"graphql error: {data['errors']}")


def _next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip()
        if section.endswith('rel="next"'):
            return section.split(";", 1)[0].strip().strip("<>")
    return None


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN env var is required", file=sys.stderr)
        return 1

    do_delete = "--delete" in sys.argv
    do_close = "--close" in sys.argv
    if do_delete and do_close:
        print("ERROR: --delete and --close are mutually exclusive", file=sys.stderr)
        return 1
    mode = "delete" if do_delete else ("close" if do_close else "dry-run")

    client = httpx.Client(
        base_url=GITHUB_API,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "github-logs-cleanup/0.1",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=30.0,
    )

    print(f"mode: {mode}\n")

    repos = list_owned_repos(client)
    print(f"scanning {len(repos)} owned repos...\n")

    total = 0
    for repo in repos:
        if repo.get("archived"):
            continue
        owner = repo["owner"]["login"]
        name = repo["name"]
        full = f"{owner}/{name}"

        issues = list(list_auto_issues(client, owner, name))
        if not issues:
            continue

        print(f"{full}: {len(issues)} issue(s) with label `{LABEL}`")
        for issue in issues:
            num = issue["number"]
            title = issue["title"]
            state = issue["state"]
            print(f"  #{num} [{state}] {title}")
            if mode == "close" and state == "open":
                close_issue(client, owner, name, num)
                print(f"    -> closed")
            elif mode == "delete":
                delete_issue(client, issue["node_id"])
                print(f"    -> deleted")
            total += 1

    print(f"\ntotal: {total} issue(s) {mode}d")
    return 0


if __name__ == "__main__":
    sys.exit(main())
