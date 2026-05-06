"""Render report dicts into MIME-ready HTML + plain text via Jinja2 templates."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.common.dates import utc_now

TEMPLATES_DIR = Path(__file__).parent / "templates"


class EmailRenderer:
    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            autoescape=select_autoescape(enabled_extensions=("j2",), default_for_string=False),
            trim_blocks=False,
            lstrip_blocks=False,
        )
        # Don't escape inside .txt.j2 templates.
        self._env.policies["json.dumps_kwargs"] = {"sort_keys": True}

    def render_weekly(self, result: dict[str, Any]) -> dict[str, str]:
        period = _format_weekly_period(result["start_date"], result["end_date"])
        ctx = {
            "subject": f"Weekly Engineering Summary - {period}",
            "period": period,
            "status": result.get("status"),
            "report": result.get("report") or {},
            "generated_at": utc_now().strftime("%Y-%m-%d %H:%M UTC"),
        }
        html = self._render("weekly.html.j2", ctx)
        text = self._render("weekly.txt.j2", ctx, autoescape=False)
        return {"subject": ctx["subject"], "html": html, "text": text}

    def render_monthly(self, result: dict[str, Any]) -> dict[str, str]:
        year_month = result["month"]
        period = _format_monthly_period(year_month)
        ctx = {
            "subject": f"Monthly Engineering Retrospective - {period}",
            "period": period,
            "status": result.get("status"),
            "report": result.get("report") or {},
            "generated_at": utc_now().strftime("%Y-%m-%d %H:%M UTC"),
        }
        html = self._render("monthly.html.j2", ctx)
        text = self._render("monthly.txt.j2", ctx, autoescape=False)
        return {"subject": ctx["subject"], "html": html, "text": text}

    def _render(self, template: str, ctx: dict[str, Any], autoescape: bool = True) -> str:
        if autoescape:
            return self._env.get_template(template).render(**ctx)
        # For plain-text templates, fetch with autoescape disabled.
        env_no_escape = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            autoescape=False,
            trim_blocks=False,
            lstrip_blocks=False,
        )
        return env_no_escape.get_template(template).render(**ctx)


def _format_weekly_period(start_iso: str, end_iso: str) -> str:
    s = date.fromisoformat(start_iso)
    e = date.fromisoformat(end_iso)
    if s.year == e.year:
        return f"{s.strftime('%B %d')} – {e.strftime('%B %d, %Y')}"
    return f"{s.strftime('%B %d, %Y')} – {e.strftime('%B %d, %Y')}"


def _format_monthly_period(year_month: str) -> str:
    y, m = year_month.split("-")
    return date(int(y), int(m), 1).strftime("%B %Y")
