"""Orchestrator: query DDB -> Bedrock -> S3 -> SNS-ready Markdown."""

from __future__ import annotations

import logging
from typing import Any

from src.common.config import Config, github_token
from src.common.logger import get_logger, log
from src.integrations.github_writer import AUTO_LABEL, GitHubWriter
from src.storage.dynamodb_store import ActivityStore, ReportStore
from src.storage.s3_archive import ReportsArchive
from src.summaries.bedrock_client import BedrockClient
from src.summaries.prompt_builder import SYSTEM_PROMPT, build_user_payload, compute_metrics
from src.summaries.report_formatter import to_markdown

logger = get_logger(__name__)


def generate_weekly(
    config: Config,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    activity = ActivityStore(config.activity_table)
    reports_table = ReportStore(config.reports_table)
    reports_s3 = ReportsArchive(config.reports_bucket)
    bedrock = BedrockClient(config.bedrock_model_id, region=config.region)

    records = activity.query_range(config.github_username, start_date, end_date)
    log(
        logger,
        logging.INFO,
        "loaded activity",
        records=len(records),
        start=start_date,
        end=end_date,
    )

    if not records:
        return {
            "status": "no_activity",
            "start_date": start_date,
            "end_date": end_date,
            "markdown": f"No tracked GitHub activity for {start_date} - {end_date}.\n",
        }

    user_payload = build_user_payload(
        config.github_username, start_date, end_date, records
    )
    report = bedrock.invoke_json(SYSTEM_PROMPT, user_payload)

    # Trust local metrics over whatever the model wrote, in case it miscounted.
    report["weekly_metrics"] = compute_metrics(records)

    markdown = to_markdown(report, start_date, end_date)
    json_key, md_key = reports_s3.put_weekly(
        config.github_username, end_date, report, markdown
    )
    reports_table.put_weekly(
        config.github_username,
        start_date,
        end_date,
        json_key,
        md_key,
        report["weekly_metrics"],
    )

    issues_created = _create_issues_from_repos(
        config,
        report.get("repositories") or [],
    )

    return {
        "status": "ok",
        "start_date": start_date,
        "end_date": end_date,
        "report": report,
        "markdown": markdown,
        "report_json_s3_key": json_key,
        "report_markdown_s3_key": md_key,
        "issues_created": issues_created,
    }


def _create_issues_from_repos(
    config: Config,
    repositories: list[dict[str, Any]],
) -> int:
    """Create one issue per item in each repo's `actionable_issues`. Idempotent on title.

    The LLM curates `actionable_issues` as a strict subset of next-step items it
    judges worth tracking. Empty array means nothing to do.
    """
    if not config.create_issues:
        return 0

    skip = set(config.skip_issue_repos)
    token = github_token(config.github_secret_arn)
    created = 0

    with GitHubWriter(token) as writer:
        for repo_data in repositories:
            repo_name = (repo_data.get("name") or "").strip()
            if not repo_name or "/" not in repo_name or repo_name in skip:
                continue
            actionable = repo_data.get("actionable_issues") or []
            if not actionable:
                continue
            owner, name = repo_name.split("/", 1)

            if config.private_repos_only:
                try:
                    if not writer.is_private(owner, name):
                        log(
                            logger,
                            logging.INFO,
                            "skipping public repo",
                            repo=repo_name,
                        )
                        continue
                except Exception as exc:
                    log(
                        logger,
                        logging.WARNING,
                        "could not check repo visibility, skipping",
                        repo=repo_name,
                        error=str(exc),
                    )
                    continue

            try:
                existing = writer.existing_open_titles(owner, name)
            except Exception as exc:
                log(
                    logger,
                    logging.WARNING,
                    "could not list existing issues",
                    repo=repo_name,
                    error=str(exc),
                )
                continue

            for item in actionable:
                title = str(item).strip()
                if not title or title in existing:
                    continue
                try:
                    writer.create_issue(owner, name, title, "", [AUTO_LABEL])
                    existing.add(title)
                    created += 1
                except Exception as exc:
                    log(
                        logger,
                        logging.WARNING,
                        "issue creation failed",
                        repo=repo_name,
                        title=title,
                        error=str(exc),
                    )

    log(logger, logging.INFO, "issues created", count=created)
    return created
