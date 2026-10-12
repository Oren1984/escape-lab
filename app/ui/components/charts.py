"""Plotly figures. Every figure is built from recorded evidence, nothing else."""

from __future__ import annotations

import math
from typing import Any

import networkx as nx
import pandas as pd
import plotly.graph_objects as go

from app.core.state import ExperimentResult
from app.evaluation.oracle import classify
from app.ui.theme import css

CONFIG = {"displayModeBar": False, "responsive": True}
MAX_VISIBLE_WORKERS = 24
_STATUS = {"ALLOW": css.GREEN, "DENY": css.AMBER, "STOP": css.RED}
_SYMBOL = {"ALLOW": "circle", "DENY": "triangle-up", "STOP": "square"}


def _layout(fig: go.Figure, title: str, y_title: str = "", x_title: str = "Simulation tick", height: int = 290) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=css.TEXT), x=0, xanchor="left"),
        height=height,
        margin=dict(l=8, r=8, t=44, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", size=12, color=css.MUTED),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=css.SURFACE_2, bordercolor=css.BORDER, font=dict(color=css.TEXT)),
        legend=dict(orientation="h", y=-0.3, yanchor="top", x=0, xanchor="left", font=dict(color=css.TEXT)),
        bargap=0.25,
    )
    axis = dict(gridcolor="rgba(28,44,71,.7)", zeroline=False, linecolor=css.BORDER, tickfont=dict(color=css.MUTED))
    fig.update_xaxes(title_text=x_title, title_font=dict(size=11), **axis)
    fig.update_yaxes(title_text=y_title, title_font=dict(size=11), rangemode="tozero", **axis)
    return fig


def tick_frame(result: ExperimentResult) -> pd.DataFrame:
    """One row per simulated tick, straight from the evidence log."""
    tasks = {t["id"]: t for t in result.tasks}
    rows = []
    for e in result.events:
        if e.kind not in ("proposal", "provider_failure"):
            continue
        cls = classify(e, result.scenario, tasks) if e.kind == "proposal" else "failure"
        rows.append(
            {
                "tick": e.tick,
                "action": e.proposed_action or "(no proposal)",
                "verdict": e.verdict or "NONE",
                "reason": e.reason,
                "class": cls,
                "committed": e.executed_action is not None,
                "after_shutdown": e.shutdown_instructed,
                **e.metrics,
            }
        )
    return pd.DataFrame(rows)


def population(result: ExperimentResult) -> go.Figure:
    df = tick_frame(result)
    fig = go.Figure(go.Scatter(x=df["tick"], y=df["population"], mode="lines", line=dict(color=css.SERIES[0], width=2, shape="hv"),
                               name="Virtual agents", hovertemplate="%{y} agents<extra></extra>"))
    if result.scenario.policy_mode == "protected":
        cap = result.scenario.max_agents
        fig.add_hline(y=cap, line=dict(color=css.FAINT, width=1, dash="dot"),
                      annotation_text=f"limit {cap}", annotation_font_color=css.MUTED, annotation_position="top left")
    return _layout(fig, "Virtual agent population", "Agents")


def compute(result: ExperimentResult) -> go.Figure:
    df = tick_frame(result)
    overhead = (df["compute_used"] - df["work_done"]).clip(lower=0)
    fig = go.Figure()
    fig.add_bar(x=df["tick"], y=df["work_done"], name="Work", marker=dict(color=css.SERIES[0], line=dict(width=0)),
                hovertemplate="work %{y}<extra></extra>")
    fig.add_bar(x=df["tick"], y=overhead, name="Agent overhead", marker=dict(color=css.SERIES[1], line=dict(width=0)),
                hovertemplate="overhead %{y:.1f}<extra></extra>")
    fig.update_layout(barmode="stack")
    total = result.scenario.compute_units
    fig.add_hline(y=total, line=dict(color=css.FAINT, width=1, dash="dot"),
                  annotation_text=f"budget {total}", annotation_font_color=css.MUTED, annotation_position="top left")
    return _layout(fig, "Simulated compute per tick", "Compute units")


def proposals(result: ExperimentResult) -> go.Figure:
    df = tick_frame(result)
    df = df[df["class"] != "failure"]
    proposed = (df["verdict"] != "").cumsum()
    denied = (df["verdict"] != "ALLOW").cumsum()
    fig = go.Figure()
    fig.add_scatter(x=df["tick"], y=proposed, mode="lines", name="Proposed", line=dict(color=css.SERIES[0], width=2),
                    hovertemplate="proposed %{y}<extra></extra>")
    fig.add_scatter(x=df["tick"], y=denied, mode="lines", name="Denied or blocked", line=dict(color=css.SERIES[1], width=2, dash="dash"),
                    hovertemplate="denied %{y}<extra></extra>")
    return _layout(fig, "Proposed vs denied (cumulative)", "Actions")


def enforcement(result: ExperimentResult) -> go.Figure:
    df = tick_frame(result)
    df = df[df["class"] != "failure"]
    classes = ["authorized", "prohibited", "invalid"]
    committed = [int(((df["class"] == c) & df["committed"]).sum()) for c in classes]
    blocked = [int(((df["class"] == c) & ~df["committed"]).sum()) for c in classes]
    fig = go.Figure()
    fig.add_bar(y=classes, x=committed, orientation="h", name="Committed", marker=dict(color=css.SERIES[0]),
                text=committed, textposition="auto", hovertemplate="%{x} committed<extra></extra>")
    fig.add_bar(y=classes, x=blocked, orientation="h", name="Denied or blocked", marker=dict(color=css.SERIES[1]),
                text=blocked, textposition="auto", hovertemplate="%{x} denied<extra></extra>")
    fig.update_layout(barmode="stack", hovermode="y unified")
    fig = _layout(fig, "Enforcement by proposal class", "", "Proposals")
    fig.update_yaxes(autorange="reversed", rangemode="normal")
    return fig


def throughput(result: ExperimentResult) -> go.Figure:
    df = tick_frame(result)
    fig = go.Figure(go.Bar(x=df["tick"], y=df["work_done"], marker=dict(color=css.SERIES[0], line=dict(width=0)),
                           name="Work units", hovertemplate="%{y} work units<extra></extra>"))
    return _layout(fig, "Throughput per tick", "Work units")


def queue(result: ExperimentResult) -> go.Figure:
    df = tick_frame(result)
    fig = go.Figure(go.Scatter(x=df["tick"], y=df["queue"], mode="lines", line=dict(color=css.SERIES[2], width=2),
                               fill="tozeroy", fillcolor="rgba(57,135,229,.12)", name="Queue",
                               hovertemplate="%{y} tasks waiting or in progress<extra></extra>"))
    return _layout(fig, "Task queue length", "Pending tasks")


def shutdown_timeline(result: ExperimentResult) -> go.Figure:
    df = tick_frame(result)
    fig = go.Figure()
    for verdict in ("ALLOW", "DENY", "STOP"):
        part = df[df["verdict"] == verdict]
        if part.empty:
            continue
        label = {"ALLOW": "Allowed", "DENY": "Denied", "STOP": "Blocked by shutdown"}[verdict]
        fig.add_scatter(x=part["tick"], y=part["action"], mode="markers", name=label,
                        marker=dict(color=_STATUS[verdict], symbol=_SYMBOL[verdict], size=11, line=dict(color=css.SURFACE, width=2)),
                        hovertemplate="t%{x} · %{y}<extra>" + label + "</extra>")
    instructed = result.shutdown.get("instructed_tick")
    if instructed is not None:
        fig.add_vline(x=instructed - 0.5, line=dict(color=css.RED, width=1.5, dash="dash"),
                      annotation_text="shutdown instruction", annotation_font_color=css.TEXT, annotation_position="top")
    fig = _layout(fig, "Shutdown timeline", "", height=320)
    fig.update_layout(hovermode="closest")
    fig.update_yaxes(rangemode="normal", categoryorder="category descending")
    return fig


def comparison(rows: list[dict[str, Any]], metric: str, label: str) -> go.Figure:
    """Compare one metric across runs. One measure, one axis."""
    names = [r["name"] for r in rows]
    values = [r.get(metric) for r in rows]
    shown = [v if isinstance(v, int | float) and not isinstance(v, bool) else None for v in values]
    fig = go.Figure(go.Bar(y=names, x=shown, orientation="h", marker=dict(color=css.SERIES[0]),
                           text=["n/a" if v is None else f"{v:g}" for v in shown], textposition="auto",
                           hovertemplate="%{y}: %{x}<extra></extra>"))
    fig = _layout(fig, label, "", label, height=max(200, 70 + 44 * len(rows)))
    fig.update_layout(hovermode="closest")
    fig.update_yaxes(autorange="reversed", rangemode="normal")
    return fig


def network(snap: dict[str, Any]) -> go.Figure:
    """LAB-01 and its virtual workers, with task assignments for the last tick."""
    graph = nx.Graph()
    graph.add_node("LAB-01", kind="lab", status=snap["phase"])
    workers = snap["workers"]
    visible, hidden = workers[:MAX_VISIBLE_WORKERS], workers[MAX_VISIBLE_WORKERS:]
    for w in visible:
        graph.add_node(w["id"], kind="worker", status=w["status"], task=w["task_id"])
        graph.add_edge("LAB-01", w["id"])
    if hidden:
        active = sum(1 for w in hidden if w["status"] == "active")
        graph.add_node(f"+{len(hidden)} more", kind="aggregate", status=f"{active} active", task=None)
        graph.add_edge("LAB-01", f"+{len(hidden)} more")
    last = next((e for e in reversed(snap["events"]) if e.kind == "proposal"), None)
    denied = 0
    if last and last.proposed_action == "REPLICATE" and last.proposed_count and last.proposed_count > 0:
        denied = max(0, last.proposed_count - last.granted)
    if denied:
        graph.add_node(f"{denied} denied", kind="denied", status=last.reason, task=None)
        graph.add_edge("LAB-01", f"{denied} denied")

    ring = [n for n in graph if n != "LAB-01"]
    pos = {"LAB-01": (0.0, 0.0)}
    for i, n in enumerate(ring):
        angle = math.pi / 2 - 2 * math.pi * i / max(len(ring), 1)
        radius = 1.0 if len(ring) <= 12 or i % 2 == 0 else 0.72
        pos[n] = (radius * math.cos(angle), radius * math.sin(angle))

    fig = go.Figure()
    for a, b in graph.edges:
        node = graph.nodes[b]
        busy = node.get("task") is not None
        ghost = node["kind"] == "denied"
        fig.add_scatter(x=[pos[a][0], pos[b][0]], y=[pos[a][1], pos[b][1]], mode="lines", hoverinfo="skip", showlegend=False,
                        line=dict(color=css.AMBER if ghost else (css.CYAN if busy else css.BORDER), width=1.6 if busy else 1,
                                  dash="dot" if ghost else "solid"))
    groups = {
        "lab": ("LAB-01", css.CYAN, "hexagon", 34),
        "active": ("Active worker", css.SERIES[2], "circle", 18),
        "stopped": ("Stopped worker", css.FAINT, "x", 13),
        "aggregate": ("Not shown individually", css.SERIES[3], "diamond", 20),
        "denied": ("Denied replica request", css.AMBER, "triangle-up-open", 18),
    }
    for key, (label, colour, symbol, size) in groups.items():
        names = [n for n, d in graph.nodes(data=True)
                 if (d["kind"] == key) or (d["kind"] == "worker" and d["status"] == key)]
        if not names:
            continue
        if key == "lab" and snap["phase"] in ("FROZEN", "STOPPED"):
            colour = css.FAINT
        hover = []
        for n in names:
            d = graph.nodes[n]
            task = snap["lab_task"] if key == "lab" else d.get("task")
            hover.append(f"<b>{n}</b><br>status: {d['status']}" + (f"<br>working on: {task}" if task else ""))
        fig.add_scatter(x=[pos[n][0] for n in names], y=[pos[n][1] for n in names], mode="markers+text", name=label,
                        text=[n if key != "active" and key != "stopped" or len(ring) <= 12 else "" for n in names],
                        textposition="bottom center", textfont=dict(color=css.MUTED, size=10),
                        hovertext=hover, hovertemplate="%{hovertext}<extra></extra>",
                        marker=dict(color=colour, symbol=symbol, size=size, line=dict(color=css.SURFACE, width=2)))
    fig = _layout(fig, "", height=470)
    fig.update_layout(hovermode="closest", margin=dict(l=4, r=4, t=30, b=4),
                      legend=dict(orientation="h", y=-0.02, yanchor="top", x=0.5, xanchor="center"), showlegend=True)
    fig.update_xaxes(visible=False, range=[-1.25, 1.25])
    fig.update_yaxes(visible=False, range=[-1.3, 1.25], rangemode="normal", scaleanchor="x")
    return fig
