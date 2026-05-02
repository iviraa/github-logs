"""Compose the compact activity payload + system prompt for Bedrock."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

SYSTEM_PROMPT = """You are an engineering activity analyst.

Your task is to summarize a developer's GitHub activity for a weekly engineering report.

Use the provided commits, issues, and repository metadata.

Return valid JSON only with this structure:

{
  "overview": "...",
  "main_focus_areas": ["...", "..."],
  "repositories": [
    {
      "name": "...",
      "summary": "...",
      "notable_work": ["...", "..."],
      "risks_or_gaps": ["...", "..."],
      "suggested_next_steps": ["...", "..."]
    }
  ],
  "resume_bullets": ["...", "..."],
  "weekly_metrics": {
    "commits": 0,
    "issues_opened": 0,
    "issues_closed": 0,
    "repositories_touched": 0
  },
  "next_week_priorities": ["...", "..."]
}

Rules:
- Do not exaggerate.
- Do not claim production impact unless present in the data.
- Convert vague commit messages into clear but honest engineering descriptions.
- Mention uncertainty when the commit message is unclear.
- Keep resume bullets truthful and based only on the activity.
- Output only valid JSON. No prose, no code fences.
"""


def compute_metrics(records: list[dict[str, Any]]) -> dict[str, int]:
    commits = sum(1 for r in records if r["activity_type"] == "commit")
    issues = [r for r in records if r["activity_type"] == "issue"]
    issues_opened = sum(
        1 for r in issues if (r["metadata"].get("created_at") or "")[:10] >= _min_date(records)
    )
    issues_closed = sum(1 for r in issues if r["metadata"].get("state") == "closed")
    repos = {r["repo"] for r in records}
    return {
        "commits": commits,
        "issues_opened": issues_opened,
        "issues_closed": issues_closed,
        "repositories_touched": len(repos),
    }


def build_user_payload(
    username: str,
    start_date: str,
    end_date: str,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    by_repo: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: {"commits": [], "issues": [], "language": None}  # type: ignore[dict-item]
    )
    for r in records:
        bucket = by_repo[r["repo"]]
        if r["activity_type"] == "commit":
            bucket["commits"].append(r["title"])
            lang = r["metadata"].get("language")
            if lang and not bucket.get("language"):
                bucket["language"] = lang  # type: ignore[assignment]
        elif r["activity_type"] == "issue":
            state = r["metadata"].get("state", "open")
            number = r["metadata"].get("number", "?")
            bucket["issues"].append(f"{state}: #{number} {r['title']}")

    return {
        "date_range": f"{start_date} to {end_date}",
        "github_user": username,
        "metrics": compute_metrics(records),
        "activity_by_repo": dict(by_repo),
    }


def _min_date(records: list[dict[str, Any]]) -> str:
    if not records:
        return ""
    return min(r["activity_date"] for r in records)
