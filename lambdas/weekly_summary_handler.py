"""Weekly Bedrock-driven summary Lambda entry point."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from src.common.config import load
from src.common.dates import utc_now, weekly_window
from src.common.logger import get_logger, log
from src.notifications.email_renderer import EmailRenderer
from src.notifications.ses_sender import SesSender
from src.summaries.summary_generator import generate_weekly

logger = get_logger(__name__)


def lambda_handler(event: dict[str, Any], _context: object) -> dict[str, Any]:
    config = load()

    end_str = event.get("end_date")
    if end_str:
        end = date.fromisoformat(end_str)
    else:
        end = utc_now().date()
    start = event.get("start_date")
    if start:
        start_d = date.fromisoformat(start)
    else:
        start_d, end = weekly_window(end)

    result = generate_weekly(config, start_d.isoformat(), end.isoformat())
    log(
        logger,
        logging.INFO,
        "generated weekly summary",
        status=result["status"],
        start=result["start_date"],
        end=result["end_date"],
    )

    rendered = EmailRenderer().render_weekly(result)
    sender = SesSender(config.sender_email, region=config.region)
    message_id = sender.send(
        config.recipient_email,
        rendered["subject"],
        rendered["html"],
        rendered["text"],
    )
    return {
        **{k: v for k, v in result.items() if k != "report"},
        "ses_message_id": message_id,
    }
