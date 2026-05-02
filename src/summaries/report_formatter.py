"""Render the structured weekly report JSON into Markdown for email."""

from __future__ import annotations

from typing import Any


def to_markdown(report: dict[str, Any], start_date: str, end_date: str) -> str:
    lines: list[str] = []
    lines.append(f"# Weekly Engineering Summary: {start_date} - {end_date}")
    lines.append("")
    lines.append("## Overview")
    lines.append(report.get("overview", "").strip())
    lines.append("")

    metrics = report.get("weekly_metrics", {})
    if metrics:
        lines.append("## Metrics")
        lines.append(f"- Commits: {metrics.get('commits', 0)}")
        lines.append(f"- Issues opened: {metrics.get('issues_opened', 0)}")
        lines.append(f"- Issues closed: {metrics.get('issues_closed', 0)}")
        lines.append(f"- Repositories touched: {metrics.get('repositories_touched', 0)}")
        lines.append("")

    focus = report.get("main_focus_areas", []) or []
    if focus:
        lines.append("## Main Focus Areas")
        for item in focus:
            lines.append(f"- {item}")
        lines.append("")

    repos = report.get("repositories", []) or []
    if repos:
        lines.append("## Repository Breakdown")
        lines.append("")
        for repo in repos:
            lines.append(f"### {repo.get('name', 'unknown')}")
            summary = repo.get("summary", "").strip()
            if summary:
                lines.append(summary)
                lines.append("")
            _bulleted(lines, "Notable work", repo.get("notable_work"))
            _bulleted(lines, "Risks/gaps", repo.get("risks_or_gaps"))
            _bulleted(lines, "Suggested next steps", repo.get("suggested_next_steps"))

    bullets = report.get("resume_bullets", []) or []
    if bullets:
        lines.append("## Resume Bullet Drafts")
        for b in bullets:
            lines.append(f"- {b}")
        lines.append("")

    nxt = report.get("next_week_priorities", []) or []
    if nxt:
        lines.append("## Next Week")
        for i, item in enumerate(nxt, 1):
            lines.append(f"{i}. {item}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _bulleted(lines: list[str], heading: str, items: list[str] | None) -> None:
    if not items:
        return
    lines.append(f"**{heading}:**")
    for item in items:
        lines.append(f"- {item}")
    lines.append("")
