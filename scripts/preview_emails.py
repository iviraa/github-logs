"""Render local HTML/text previews of the weekly and monthly email templates.

Usage:
    cd github-logs
    source .venv/bin/activate
    pip install -r requirements.txt   # if jinja2 isn't installed yet
    python -m scripts.preview_emails

Outputs:
    docs/email_preview/weekly.html
    docs/email_preview/weekly.txt
    docs/email_preview/monthly.html
    docs/email_preview/monthly.txt

Open in a browser:
    open docs/email_preview/weekly.html
"""

from __future__ import annotations

import sys
from pathlib import Path

from src.notifications.email_renderer import EmailRenderer

PREVIEW_DIR = Path(__file__).parent.parent / "docs" / "email_preview"


WEEKLY_SAMPLE: dict = {
    "status": "ok",
    "start_date": "2026-04-27",
    "end_date": "2026-05-04",
    "report": {
        "headline": "A focused week on the data lake and email pipeline.",
        "overview": (
            "This week you focused on building out the analytics layer for "
            "github-logs - the project went from a working MVP to a "
            "serverless data lake with monthly retrospectives. Most of the "
            "remaining work is polish."
        ),
        "main_focus_areas": [
            "Glue + Athena analytics layer",
            "SAM deployment fixes",
            "SES HTML email pipeline",
        ],
        "repositories": [
            {
                "name": "iviraa/github-logs",
                "summary": (
                    "Added the analytics tier (processed S3 zone, Glue "
                    "Crawler, Athena workgroup) plus a monthly retrospective "
                    "Lambda that queries Athena. Replaced the SNS plain-text "
                    "email pipeline with SES + Jinja2 HTML templates."
                ),
                "notable_work": [
                    "Wrote flattened activity records to a partitioned processed S3 tier",
                    "Added Glue database, crawler, and Athena workgroup via SAM",
                    "Implemented monthly retrospective Lambda with Athena-backed aggregates",
                    "Replaced SNS plain-text emails with SES HTML emails",
                ],
                "risks_or_gaps": [
                    "No automated tests around the Athena query path yet",
                    "Lambda zip is larger than needed; a .samignore would tighten it",
                ],
                "suggested_next_steps": [
                    "Add Athena-enriched aggregates to the weekly summary prompt",
                    "Trim docs/scripts/Makefile out of the deployment package",
                ],
            }
        ],
        "resume_bullets": [
            (
                "Built a serverless GitHub activity intelligence system on AWS "
                "using Lambda, DynamoDB, S3, Glue, Athena, Bedrock, and SES, "
                "with EventBridge orchestration across daily, weekly, and "
                "monthly schedules."
            ),
            (
                "Designed an operational/analytical data split (DynamoDB for "
                "current state, S3+Glue+Athena for history) so weekly reports "
                "stay sub-second and monthly retrospectives can run SQL "
                "aggregates without affecting the live system."
            ),
        ],
        "weekly_metrics": {
            "commits": 12,
            "issues_opened": 0,
            "issues_closed": 0,
            "repositories_touched": 1,
        },
        "next_week_priorities": [
            "Push the repo to GitHub",
            "Add Athena-enriched weekly summary",
            "Iterate on email template based on first real-world rendering",
        ],
    },
}


MONTHLY_SAMPLE: dict = {
    "status": "ok",
    "month": "2026-04",
    "report": {
        "headline": (
            "April was dominated by the github-logs project - a serverless "
            "GitHub activity pipeline went from scaffold to a fully wired data "
            "lake with weekly and monthly LLM-generated reports."
        ),
        "themes": [
            "AWS serverless (Lambda + EventBridge)",
            "Data lake (S3 + Glue + Athena)",
            "LLM integration (Bedrock + Claude Haiku)",
        ],
        "by_repo": [
            {
                "name": "iviraa/github-logs",
                "summary": (
                    "From zero to deployed end-to-end. Started as a Python + "
                    "SAM scaffold; ended with daily collector, weekly summary, "
                    "monthly retrospective, all running on EventBridge schedules."
                ),
                "what_shipped": [
                    "Daily GitHub activity collector with idempotent batch writes",
                    "Weekly Bedrock-driven summary plus monthly Athena-backed retrospective",
                    "Glue crawler, data catalog, Athena workgroup",
                    "SES HTML email pipeline",
                ],
                "open_threads": [
                    "Tier-2 features (per-repo GSI, TODO/FIXME scanner)",
                    "Tighter Lambda zip via .samignore",
                ],
            }
        ],
        "month_over_month": {
            "commits_this_month": 47,
            "commits_prior_month": 0,
            "narrative": (
                "First active month for the project; no prior-month "
                "comparison available."
            ),
        },
        "resume_bullets": [
            (
                "Designed and deployed a serverless data intelligence pipeline "
                "on AWS spanning ingestion, partitioned storage, schema "
                "discovery via Glue, SQL analytics via Athena, and "
                "LLM-generated reporting via Bedrock."
            ),
            (
                "Implemented an operational/analytical data split (DynamoDB "
                "for current state, S3+Glue+Athena for history) so weekly "
                "summaries stay sub-second and monthly retrospectives can run "
                "SQL aggregates without affecting the live system."
            ),
        ],
        "next_month_focus": [
            "Push project to GitHub",
            "Add Athena-enriched weekly reports",
            "Run for several real weeks to validate the prompt and email layout",
        ],
    },
}


def main() -> int:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    renderer = EmailRenderer()

    weekly = renderer.render_weekly(WEEKLY_SAMPLE)
    monthly = renderer.render_monthly(MONTHLY_SAMPLE)

    (PREVIEW_DIR / "weekly.html").write_text(weekly["html"])
    (PREVIEW_DIR / "weekly.txt").write_text(weekly["text"])
    (PREVIEW_DIR / "monthly.html").write_text(monthly["html"])
    (PREVIEW_DIR / "monthly.txt").write_text(monthly["text"])

    print(f"wrote previews to {PREVIEW_DIR}")
    print("  weekly:  open docs/email_preview/weekly.html")
    print("  monthly: open docs/email_preview/monthly.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
