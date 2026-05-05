"""Monthly Bedrock-driven retrospective Lambda entry point.

Triggered first of each month at 21:00 UTC. Queries Athena over the prior
month's data, asks Bedrock for a structured retrospective, emails the result.
"""

from __future__ import annotations

import logging
import os
from datetime import date
from typing import Any

from src.common.config import load
from src.common.dates import utc_now
from src.common.logger import get_logger, log
from src.notifications.sns_notifier import SnsNotifier
from src.summaries.monthly_summary_generator import generate_monthly

logger = get_logger(__name__)


def lambda_handler(event: dict[str, Any], _context: object) -> dict[str, Any]:
    config = load()
    workgroup = _require("ATHENA_WORKGROUP")
    database = _require("GLUE_DATABASE")

    year_month = event.get("year_month") or _prior_month_str(utc_now().date())

    result = generate_monthly(config, workgroup, database, year_month)
    log(
        logger,
        logging.INFO,
        "generated monthly summary",
        status=result["status"],
        month=year_month,
    )

    notifier = SnsNotifier(config.sns_topic_arn)
    subject = f"Monthly Engineering Retrospective: {year_month}"
    message_id = notifier.publish(subject, result["markdown"])
    return {**{k: v for k, v in result.items() if k != "report"}, "sns_message_id": message_id}


def _prior_month_str(today: date) -> str:
    y, m = today.year, today.month
    if m == 1:
        return f"{y - 1:04d}-12"
    return f"{y:04d}-{m - 1:02d}"


def _require(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"missing required env var: {key}")
    return value
