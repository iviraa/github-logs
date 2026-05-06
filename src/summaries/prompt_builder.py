"""Compose the compact activity payload + system prompt for Bedrock."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

SYSTEM_PROMPT = """You are an engineering activity analyst.

Your task is to summarize a developer's GitHub activity for a weekly engineering report.

Use the provided commits, issues, and repository metadata.

Return valid JSON only with this structure:

{
  "headline": "...",
  "overview": "...",
  "main_focus_areas": ["...", "..."],
  "repositories": [
    {
      "name": "...",
      "summary": "...",
      "notable_work": ["...", "..."],
      "risks_or_gaps": ["...", "..."],
      "suggested_next_steps": ["...", "..."],
      "actionable_issues": ["..."]
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
- "headline" is one short sentence (max 70 characters), the punchline of the week.
- "overview" is 2-3 sentences expanding on the headline with concrete detail.
- "actionable_issues" is a STRICT SUBSET of "suggested_next_steps". Apply tech-lead
  judgment: only include an item if it describes a concrete unit of work that fits
  in a single pull request, has a clear acceptance criterion, and is genuinely
  worth tracking as a discrete issue. SKIP items that are vague, multi-week
  projects, generic observations, recommendations to "consider X", documentation
  housekeeping, or trivial notes that a developer would not want as a tracked
  ticket. Quality over quantity. An empty array is the correct answer when
  nothing qualifies.
- Do not exaggerate.
- Do not claim production impact unless present in the data.
- Convert vague commit messages into clear but honest engineering descriptions.
- Mention uncertainty when the commit message is unclear.
- Keep resume bullets truthful and based only on the activity.
- Do NOT use em dashes (—) anywhere. Use commas, periods, parentheses, or semicolons in their place. This applies to every string field, including overview, summary, and bullets.
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
