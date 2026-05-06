"""Orchestrator: Athena -> Bedrock -> S3 -> SNS for monthly retrospectives."""

from __future__ import annotations

import calendar
import logging
from datetime import date
from typing import Any

from src.common.config import Config
from src.common.logger import get_logger, log
from src.storage.athena_client import AthenaClient
from src.storage.dynamodb_store import ReportStore
from src.storage.s3_archive import ReportsArchive
from src.summaries.bedrock_client import BedrockClient
from src.summaries.monthly_prompt_builder import (
    MONTHLY_SYSTEM_PROMPT,
    build_user_payload,
)
from src.summaries.summary_generator import _create_issues_from_repos

logger = get_logger(__name__)

ACTIVITY_TABLE = "activity"  # Glue Crawler-discovered table inside the database


def generate_monthly(
    config: Config,
    workgroup: str,
    database: str,
    year_month: str,
) -> dict[str, Any]:
    """year_month is 'YYYY-MM'."""
    start_date, end_date = _month_bounds(year_month)
    prior_start, prior_end = _month_bounds(_prior_month(year_month))

    athena = AthenaClient(workgroup, database, region=config.region)
    bedrock = BedrockClient(config.bedrock_model_id, region=config.region)
    reports_table = ReportStore(config.reports_table)
    reports_s3 = ReportsArchive(config.reports_bucket)

    metrics = _aggregate_metrics(athena, start_date, end_date)
    log(
        logger,
        logging.INFO,
        "monthly metrics",
        month=year_month,
        commits=metrics.get("commits"),
        issues=metrics.get("issues"),
        repos=metrics.get("repos"),
    )

    if (metrics.get("commits") or 0) == 0 and (metrics.get("issues") or 0) == 0:
        return {
            "status": "no_activity",
            "month": year_month,
            "markdown": f"No tracked GitHub activity for {year_month}.\n",
        }

    by_repo = _by_repo(athena, start_date, end_date)
    weekly = _weekly_breakdown(athena, start_date, end_date)
    prior = _aggregate_metrics(athena, prior_start, prior_end)

    payload = build_user_payload(year_month, metrics, by_repo, weekly, prior)
    report = bedrock.invoke_json(MONTHLY_SYSTEM_PROMPT, payload)

    # Trust deterministic counts over whatever the model returns.
    this_commits = int(metrics.get("commits") or 0)
    prior_commits = int(prior.get("commits") or 0)
    report["month_over_month"] = report.get("month_over_month") or {}
    report["month_over_month"]["commits_this_month"] = this_commits
    report["month_over_month"]["commits_prior_month"] = prior_commits
    if prior_commits > 0:
        delta = (this_commits - prior_commits) * 100 / prior_commits
        report["month_over_month"]["commit_change_pct"] = round(delta)
    else:
        # No prior data to compare against; drop any stale value the model may have hallucinated.
        report["month_over_month"].pop("commit_change_pct", None)

    markdown = _to_markdown(report, year_month)
    json_key, md_key = reports_s3.put_weekly(  # reuses the same path scheme
        config.github_username, end_date, report, markdown
    )
    reports_table.put_weekly(
        config.github_username,
        start_date,
        end_date,
        json_key,
        md_key,
        {"commits": metrics.get("commits", 0), "issues": metrics.get("issues", 0)},
    )

    issues_created = _create_issues_from_repos(
        config,
        report.get("by_repo") or [],
    )

    return {
        "status": "ok",
        "month": year_month,
        "report": report,
        "markdown": markdown,
        "report_json_s3_key": json_key,
        "report_markdown_s3_key": md_key,
        "issues_created": issues_created,
    }


# -- aggregation queries -------------------------------------------------

def _aggregate_metrics(
    athena: AthenaClient, start_date: str, end_date: str
) -> dict[str, Any]:
    sql = f"""
      SELECT
        count_if(activity_type='commit') AS commits,
        count_if(activity_type='issue') AS issues,
        count(DISTINCT repo) AS repos,
        coalesce(sum(commit_additions), 0) AS additions,
        coalesce(sum(commit_deletions), 0) AS deletions
      FROM {ACTIVITY_TABLE}
      WHERE activity_date BETWEEN '{start_date}' AND '{end_date}'
    """
    rows = athena.query(sql)
    if not rows:
        return {"commits": 0, "issues": 0, "repos": 0, "additions": 0, "deletions": 0}
    r = rows[0]
    return {k: _to_int(v) for k, v in r.items()}


def _by_repo(
    athena: AthenaClient, start_date: str, end_date: str
) -> list[dict[str, Any]]:
    sql = f"""
      SELECT
        repo,
        count_if(activity_type='commit') AS commits,
        count_if(activity_type='issue') AS issues,
        coalesce(sum(commit_additions), 0) AS additions,
        coalesce(sum(commit_deletions), 0) AS deletions
      FROM {ACTIVITY_TABLE}
      WHERE activity_date BETWEEN '{start_date}' AND '{end_date}'
      GROUP BY repo
      ORDER BY commits DESC, issues DESC
    """
    return [
        {k: (_to_int(v) if k != "repo" else v) for k, v in row.items()}
        for row in athena.query(sql)
    ]


def _weekly_breakdown(
    athena: AthenaClient, start_date: str, end_date: str
) -> list[dict[str, Any]]:
    sql = f"""
      SELECT
        date_trunc('week', cast(activity_date AS date)) AS week_start,
        count_if(activity_type='commit') AS commits,
        count_if(activity_type='issue') AS issues
      FROM {ACTIVITY_TABLE}
      WHERE activity_date BETWEEN '{start_date}' AND '{end_date}'
      GROUP BY 1
      ORDER BY 1
    """
    return [
        {
            "week_start": row.get("week_start"),
            "commits": _to_int(row.get("commits")),
            "issues": _to_int(row.get("issues")),
        }
        for row in athena.query(sql)
    ]


# -- helpers -------------------------------------------------------------

def _to_int(v: Any) -> int:
    try:
        return int(v) if v is not None else 0
    except (TypeError, ValueError):
        return 0


def _month_bounds(year_month: str) -> tuple[str, str]:
    y, m = map(int, year_month.split("-"))
    last_day = calendar.monthrange(y, m)[1]
    return f"{y:04d}-{m:02d}-01", f"{y:04d}-{m:02d}-{last_day:02d}"


def _prior_month(year_month: str) -> str:
    y, m = map(int, year_month.split("-"))
    if m == 1:
        return f"{y - 1:04d}-12"
    return f"{y:04d}-{m - 1:02d}"


def _to_markdown(report: dict[str, Any], year_month: str) -> str:
    lines: list[str] = [f"# Monthly Engineering Retrospective: {year_month}", ""]
    lines.append("## Headline")
    lines.append(report.get("headline", "").strip())
    lines.append("")

    mom = report.get("month_over_month", {}) or {}
    lines.append("## Month-over-Month")
    lines.append(f"- Commits this month: {mom.get('commits_this_month', 0)}")
    lines.append(f"- Commits prior month: {mom.get('commits_prior_month', 0)}")
    change_pct = mom.get("commit_change_pct")
    if isinstance(change_pct, (int, float)):
        lines.append(f"- Change: {int(change_pct):+d}%")
    if mom.get("narrative"):
        lines.append("")
        lines.append(mom["narrative"])
    lines.append("")

    themes = report.get("themes") or []
    if themes:
        lines.append("## Themes")
        for t in themes:
            lines.append(f"- {t}")
        lines.append("")

    repos = report.get("by_repo") or []
    if repos:
        lines.append("## By Repository")
        for repo in repos:
            lines.append(f"### {repo.get('name', 'unknown')}")
            if repo.get("summary"):
                lines.append(repo["summary"])
                lines.append("")
            shipped = repo.get("what_shipped") or []
            if shipped:
                lines.append("**Shipped:**")
                for s in shipped:
                    lines.append(f"- {s}")
                lines.append("")
            open_threads = repo.get("open_threads") or []
            if open_threads:
                lines.append("**Open threads:**")
                for o in open_threads:
                    lines.append(f"- {o}")
                lines.append("")

    bullets = report.get("resume_bullets") or []
    if bullets:
        lines.append("## Resume Bullet Drafts")
        for b in bullets:
            lines.append(f"- {b}")
        lines.append("")

    nxt = report.get("next_month_focus") or []
    if nxt:
        lines.append("## Next Month Focus")
        for i, item in enumerate(nxt, 1):
            lines.append(f"{i}. {item}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
