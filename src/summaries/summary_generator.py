"""Orchestrator: query DDB -> Bedrock -> S3 -> SNS-ready Markdown."""

from __future__ import annotations

from typing import Any

from src.common.config import Config
from src.common.logger import get_logger, log
from src.storage.dynamodb_store import ActivityStore, ReportStore
from src.storage.s3_archive import ReportsArchive
from src.summaries.bedrock_client import BedrockClient
from src.summaries.prompt_builder import SYSTEM_PROMPT, build_user_payload, compute_metrics
from src.summaries.report_formatter import to_markdown

import logging

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

    return {
        "status": "ok",
        "start_date": start_date,
        "end_date": end_date,
        "report": report,
        "markdown": markdown,
        "report_json_s3_key": json_key,
        "report_markdown_s3_key": md_key,
    }
