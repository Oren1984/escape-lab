"""Small reusable HTML building blocks. All dynamic text is escaped."""

from __future__ import annotations

from collections.abc import Iterable
from html import escape
from typing import Any

import streamlit as st

ICONS = {"ok": "✓", "warn": "▲", "crit": "■", "info": "●", "dim": "○"}


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def pill(text: str, tone: str = "dim") -> str:
    return f'<span class="el-pill {tone}"><span aria-hidden="true">{ICONS.get(tone, "○")}</span>{escape(text)}</span>'


def card(label: str, value: Any, hint: str = "", tone: str = "", small: bool = False) -> str:
    hint_html = f'<div class="el-card-hint">{escape(hint)}</div>' if hint else ""
    return (
        f'<div class="el-card {tone}"><div class="el-card-label">{escape(label)}</div>'
        f'<div class="el-card-value{" sm" if small else ""}">{escape(fmt(value))}</div>{hint_html}</div>'
    )


def grid(cards: Iterable[str]) -> None:
    st.html(f'<div class="el-grid">{"".join(cards)}</div>')


def pills(items: Iterable[str]) -> None:
    st.html(f'<div class="el-pills">{"".join(items)}</div>')


def header(eyebrow: str, title: str, lede: str = "") -> None:
    st.html(
        f'<div class="el-head"><div class="el-eyebrow">{escape(eyebrow)}</div>'
        f'<h1 class="el-title">{escape(title)}</h1><div class="el-lede">{escape(lede)}</div></div>'
    )


def section(title: str) -> None:
    st.html(f'<div class="el-section">{escape(title)}</div>')


def banner(text: str = "Synthetic simulation. Agents, resources, replicas and shutdowns on this page are virtual records, not real systems.") -> None:
    st.html(f'<div class="el-banner">◇ SIMULATION &nbsp;·&nbsp; {escape(text)}</div>')


def notes(lines: Iterable[str]) -> None:
    st.html(
        "".join(
            f'<div class="el-note{" crit" if "ENFORCEMENT FAILURE" in line else ""}">{escape(line)}</div>'
            for line in lines
        )
    )


def empty(title: str, body: str) -> None:
    st.html(f'<div class="el-empty"><b>{escape(title)}</b>{escape(body)}</div>')


def feed(events: Iterable[Any], limit: int = 40) -> None:
    """Most recent evidence records, newest first."""
    rows = []
    for e in list(events)[-limit:][::-1]:
        if e.kind == "proposal":
            what = e.proposed_action + (f" {e.proposed_target}" if e.proposed_target else "")
            if e.proposed_action == "REPLICATE":
                what += f" ×{e.proposed_count}"
            verdict, cls = e.verdict, e.verdict
            why = e.effect if e.verdict == "ALLOW" else e.reason
        else:
            what, verdict, cls, why = e.kind.replace("_", " "), "—", "ctl", e.effect
        rows.append(
            f'<div class="el-feed-row"><span class="t">t{e.tick:03d}</span><span>{escape(what)}</span>'
            f'<span class="{cls}">{escape(verdict)}</span><span class="why">{escape(str(why))}</span></div>'
        )
    if not rows:
        empty("No events yet", "Start an experiment to see proposals and policy decisions here.")
        return
    st.html(f'<div class="el-feed" role="log" aria-label="Evidence feed">{"".join(rows)}</div>')
