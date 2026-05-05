"""System prompt + payload builder for the monthly retrospective."""

from __future__ import annotations

from typing import Any

MONTHLY_SYSTEM_PROMPT = """You are an engineering activity analyst preparing a
monthly retrospective for a single developer.

You receive aggregated GitHub activity for one month plus a small comparison
window (the prior month). Use SQL-style aggregates that are already computed -
do not invent metrics that aren't in the data.

Return valid JSON only with this structure:

{
  "month": "YYYY-MM",
  "headline": "...",
  "themes": ["...", "..."],
  "by_repo": [
    {
      "name": "...",
      "summary": "...",
      "what_shipped": ["...", "..."],
      "open_threads": ["...", "..."]
    }
  ],
  "month_over_month": {
    "commit_change_pct": <signed int>,
    "commits_this_month": <int>,
    "commits_prior_month": <int>,
    "narrative": "..."
  },
  "resume_bullets": ["...", "..."],
  "next_month_focus": ["...", "..."]
}

Rules:
- Do not exaggerate or claim production impact unless it appears in the data.
- If there are zero commits, say so plainly; don't fabricate work.
- Resume bullets must be grounded in repo names and themes from the data only.
- Output valid JSON. No prose, no code fences.
"""


def build_user_payload(
    month: str,
    metrics: dict[str, Any],
    by_repo: list[dict[str, Any]],
    weekly_breakdown: list[dict[str, Any]],
    prior_month_metrics: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "month": month,
        "metrics_this_month": metrics,
        "metrics_prior_month": prior_month_metrics or {},
        "by_repo": by_repo,
        "weekly_breakdown": weekly_breakdown,
    }
