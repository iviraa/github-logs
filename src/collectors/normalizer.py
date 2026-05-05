"""Pure functions: raw GitHub JSON -> normalized activity records.

Records use the schema documented in docs/architecture.md. No I/O here, so
these functions are easy to unit-test against fixtures in sample_data/.
"""

from __future__ import annotations

from typing import Any


def normalize_commit(
    repo_full_name: str,
    primary_language: str | None,
    commit: dict[str, Any],
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sha = commit["sha"]
    short_sha = sha[:7]
    author_date = commit["commit"]["author"]["date"]
    message = commit["commit"]["message"].splitlines()[0][:300]

    stats = (detail or {}).get("stats", {})
    files = (detail or {}).get("files", []) or []

    return {
        "activity_id": f"commit#{repo_full_name}#{sha}",
        "activity_type": "commit",
        "repo": repo_full_name,
        "activity_date": author_date[:10],
        "timestamp": author_date,
        "title": message,
        "url": commit.get("html_url", ""),
        "metadata": {
            "sha": sha,
            "short_sha": short_sha,
            "additions": stats.get("additions", 0),
            "deletions": stats.get("deletions", 0),
            "files_changed": len(files),
            "language": primary_language,
        },
    }


def normalize_issue(
    repo_full_name: str,
    issue: dict[str, Any],
) -> dict[str, Any]:
    number = issue["number"]
    updated_at = issue["updated_at"]
    return {
        "activity_id": f"issue#{repo_full_name}#{number}",
        "activity_type": "issue",
        "repo": repo_full_name,
        "activity_date": updated_at[:10],
        "timestamp": updated_at,
        "title": issue.get("title", "")[:300],
        "url": issue.get("html_url", ""),
        "metadata": {
            "number": number,
            "state": issue.get("state", "open"),
            "created_at": issue.get("created_at"),
            "closed_at": issue.get("closed_at"),
            "labels": [lbl.get("name") for lbl in issue.get("labels", []) if lbl.get("name")],
            "assignee": (issue.get("assignee") or {}).get("login"),
        },
    }


def to_ddb_keys(username: str, record: dict[str, Any]) -> dict[str, str]:
    """Compose PK/SK for the DeveloperActivity table."""
    pk = f"USER#{username}"
    sk = (
        f"ACTIVITY#{record['activity_date']}"
        f"#{record['repo']}"
        f"#{record['activity_type']}"
        f"#{record['activity_id'].rsplit('#', 1)[-1]}"
    )
    return {"PK": pk, "SK": sk}


def flatten_for_analytics(record: dict[str, Any]) -> dict[str, Any]:
    """Flatten a normalized activity record into a SQL-friendly shape for Athena.

    Keeps a single schema across commits and issues by promoting metadata fields
    into typed top-level columns; null for the type that doesn't apply.
    """
    base: dict[str, Any] = {
        "activity_id": record["activity_id"],
        "activity_type": record["activity_type"],
        "repo": record["repo"],
        "activity_date": record["activity_date"],
        "timestamp": record["timestamp"],
        "title": record["title"],
        "url": record.get("url"),
        "commit_sha": None,
        "commit_short_sha": None,
        "commit_additions": None,
        "commit_deletions": None,
        "commit_files_changed": None,
        "commit_language": None,
        "issue_number": None,
        "issue_state": None,
        "issue_created_at": None,
        "issue_closed_at": None,
        "issue_labels": None,
        "issue_assignee": None,
    }
    md = record.get("metadata", {}) or {}
    if record["activity_type"] == "commit":
        base["commit_sha"] = md.get("sha")
        base["commit_short_sha"] = md.get("short_sha")
        base["commit_additions"] = md.get("additions", 0)
        base["commit_deletions"] = md.get("deletions", 0)
        base["commit_files_changed"] = md.get("files_changed", 0)
        base["commit_language"] = md.get("language")
    elif record["activity_type"] == "issue":
        base["issue_number"] = md.get("number")
        base["issue_state"] = md.get("state")
        base["issue_created_at"] = md.get("created_at")
        base["issue_closed_at"] = md.get("closed_at")
        base["issue_labels"] = md.get("labels", [])
        base["issue_assignee"] = md.get("assignee")
    return base
