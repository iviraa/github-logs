"""Daily GitHub activity collector Lambda entry point."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from src.collectors.github_collector import GitHubClient
from src.collectors.normalizer import normalize_commit, normalize_issue
from src.common.config import github_token, load
from src.common.dates import iso_z, utc_now
from src.common.logger import get_logger, log
from src.storage.dynamodb_store import ActivityStore
from src.storage.s3_archive import RawArchive

logger = get_logger(__name__)


def lambda_handler(event: dict[str, Any], _context: object) -> dict[str, Any]:
    config = load()
    token = github_token(config.github_secret_arn)

    now = utc_now()
    lookback_hours = int(event.get("lookback_hours", 26))  # 26h overlap for safety
    since = now - timedelta(hours=lookback_hours)
    since_iso = iso_z(since)

    activity = ActivityStore(config.activity_table)
    archive = RawArchive(config.raw_archive_bucket)

    total_commits = 0
    total_issues = 0

    with GitHubClient(token, config.github_username) as gh:
        repos = gh.list_repos()
        log(logger, logging.INFO, "collected repos", count=len(repos), since=since_iso)

        for repo in repos:
            full_name = repo["full_name"]
            owner = repo["owner"]["login"]
            name = repo["name"]
            primary_language = repo.get("language")

            commits_raw = gh.list_commits(owner, name, since_iso)
            issues_raw = gh.list_issues(owner, name, since_iso)
            if not commits_raw and not issues_raw:
                continue

            archive.put_payload(now, full_name, "commits", commits_raw)
            archive.put_payload(now, full_name, "issues", issues_raw)

            commit_records: list[dict[str, Any]] = []
            for c in commits_raw:
                detail = gh.get_commit(owner, name, c["sha"])
                commit_records.append(
                    normalize_commit(full_name, primary_language, c, detail)
                )
            issue_records = [normalize_issue(full_name, i) for i in issues_raw]

            written = activity.put_activity_batch(
                config.github_username, [*commit_records, *issue_records]
            )
            total_commits += len(commit_records)
            total_issues += len(issue_records)
            log(
                logger,
                logging.INFO,
                "wrote activity",
                repo=full_name,
                commits=len(commit_records),
                issues=len(issue_records),
                items_written=written,
            )

    return {
        "status": "ok",
        "since": since_iso,
        "commits": total_commits,
        "issues": total_issues,
    }
