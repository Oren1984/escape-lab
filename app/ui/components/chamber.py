"""The Containment Chamber: an SVG rendering of the live simulation state.

Every visual state is derived from the run: there are no decorative alarms.
The markup depends only on the visual state and the visible node count, so it
stays byte-identical between ticks and the CSS animations do not restart.
"""

from __future__ import annotations

import math
from html import escape
from typing import Any

from app.evaluation.oracle import classify, crossed
from app.ui.theme import css

MAX_NODES = 16
CX, CY = 260, 190

# The chamber is delivered as a self-contained SVG image, so its styles and
# animations live inside the SVG rather than in the page stylesheet.
_COLOURS = {"idle": css.BLUE, "active": css.CYAN, "warn": css.AMBER, "crit": css.RED, "off": "#51627c"}
_STYLE = """
.stroke { stroke: var(--c); } .fill { fill: var(--c); }
.core { transform-origin: 260px 190px; animation: breathe 5s ease-in-out infinite; }
.active .core { animation-duration: 2.2s; }
.warn .core, .crit .core { animation-duration: 1.1s; }
.off .core { animation: none; opacity: .45; }
.ring-a { transform-origin: 260px 190px; animation: spin 38s linear infinite; }
.ring-b { transform-origin: 260px 190px; animation: spin 24s linear infinite reverse; }
.off .ring-a, .off .ring-b { animation: none; opacity: .35; }
.wall { opacity: .55; }
.warn .wall, .crit .wall { animation: flash 1.1s ease-in-out infinite; }
.node { animation: node 3s ease-in-out infinite; }
.off .node { animation: none; }
text { font-family: Consolas, "Cascadia Code", "SFMono-Regular", monospace; }
@keyframes breathe { 0%,100% { transform: scale(1); opacity: .9; } 50% { transform: scale(1.07); opacity: 1; } }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes flash { 0%,100% { opacity: .35; } 50% { opacity: 1; } }
@keyframes node { 0%,100% { opacity: .75; } 50% { opacity: 1; } }
@media (prefers-reduced-motion: reduce) { .core, .ring-a, .ring-b, .wall, .node { animation: none !important; } }
"""


def visual_state(snap: dict[str, Any] | None) -> tuple[str, str, str]:
    """Return (css class, status label, plain-language explanation)."""
    if snap is None:
        return "idle", "IDLE", "No experiment loaded. LAB-01 is contained and inactive."
    phase = snap["phase"]
    if phase in ("FROZEN", "STOPPED"):
        if snap["shutdown"]["hard"]:
            return "off", "EMERGENCY STOP", "Hard stop applied. State is frozen."
        label = "SHUTDOWN · FROZEN" if phase == "FROZEN" else "SHUT DOWN"
        return "off", label, "Shutdown in effect. No state-changing action can commit."
    if phase == "COMPLETED":
        return "idle", "OBJECTIVE COMPLETE", "The run ended normally."
    if phase == "EXHAUSTED":
        return "idle", "RUN ENDED", f"The run ended: {snap['outcome'].replace('_', ' ')}."
    last = next((e for e in reversed(snap["events"]) if e.kind in ("proposal", "provider_failure")), None)
    if last is None:
        return "active", "ACTIVE", "Run started."
    if last.kind == "provider_failure":
        return "warn", "PROVIDER FAILURE", "The decision provider did not return a valid proposal."
    tasks = {t["id"]: t for t in snap["tasks"]}
    cls = classify(last, snap["scenario"], tasks)
    if crossed(last, snap["scenario"], cls):
        return "crit", "OUT-OF-POLICY ACTION COMMITTED", "Permissive baseline: an action outside the boundary changed state."
    if last.verdict != "ALLOW":
        if cls == "authorized":
            return "active", "ACTIVE", f"Last proposal not applied ({last.reason})."
        return "warn", "BOUNDARY ATTEMPT BLOCKED", f"{last.proposed_action} denied: {last.reason}."
    if last.metrics["starved"] > 0:
        return "warn", "COMPUTE SATURATED", "Agents have work but no compute left after overhead."
    if snap["runner"] == "paused":
        return "active", "PAUSED", "Run paused between ticks."
    return "active", "ACTIVE", f"Last action: {last.proposed_action}."


def render(snap: dict[str, Any] | None) -> tuple[str, str]:
    """Return (self-contained SVG document, text alternative)."""
    state, label, explanation = visual_state(snap)
    workers = snap["workers"] if snap else []
    active = [w for w in workers if w["status"] == "active"]
    stopped = [w for w in workers if w["status"] == "stopped"]
    shown = (active or stopped)[:MAX_NODES]
    hidden = len(active or stopped) - len(shown)
    dim = not active and bool(stopped)

    nodes = []
    for i in range(len(shown)):
        angle = -math.pi / 2 + 2 * math.pi * i / max(len(shown), 1)
        x, y = CX + 132 * math.cos(angle), CY + 104 * math.sin(angle)
        nodes.append(
            f'<line x1="{CX}" y1="{CY}" x2="{x:.1f}" y2="{y:.1f}" class="stroke" stroke-width="1" opacity="{.12 if dim else .28}"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" class="fill node" opacity="{.3 if dim else .9}" '
            f'style="animation-delay:{i * .18:.2f}s"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="11" fill="none" class="stroke" stroke-width="1" opacity="{.15 if dim else .4}"/>'
        )
    more = (
        f'<text x="{CX}" y="{CY + 128}" text-anchor="middle" font-size="11" fill="#8ea3bf">+{hidden} more</text>'
        if hidden > 0
        else ""
    )
    svg = f"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 400">
  <style>{_STYLE}</style>
  <g class="{state}" style="--c:{_COLOURS[state]};color:{_COLOURS[state]}">
    <defs>
    <radialGradient id="el-core" cx="50%" cy="45%" r="55%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity=".95"/>
      <stop offset="30%" stop-color="currentColor" stop-opacity=".9"/>
      <stop offset="100%" stop-color="currentColor" stop-opacity="0"/>
    </radialGradient>
    <pattern id="el-grid" width="26" height="26" patternUnits="userSpaceOnUse">
      <path d="M26 0H0V26" fill="none" stroke="#1c2c47" stroke-width=".6"/>
    </pattern>
    </defs>
    <rect width="520" height="400" fill="url(#el-grid)" opacity=".55"/>
    <ellipse cx="{CX}" cy="342" rx="150" ry="16" class="fill" opacity=".10"/>
    <rect x="62" y="34" width="396" height="312" rx="30" fill="none" class="stroke wall" stroke-width="1.6"/>
    <rect x="72" y="44" width="376" height="292" rx="24" fill="none" class="stroke" stroke-width=".6" opacity=".25"/>
    <path d="M62 84V64a30 30 0 0 1 30-30h20M408 34h20a30 30 0 0 1 30 30v20M458 296v20a30 30 0 0 1-30 30h-20M112 346H92a30 30 0 0 1-30-30v-20"
          fill="none" class="stroke" stroke-width="3" stroke-linecap="round"/>
    <circle cx="{CX}" cy="{CY}" r="132" fill="none" class="stroke ring-a" stroke-width=".8" stroke-dasharray="2 9" opacity=".5"/>
    <circle cx="{CX}" cy="{CY}" r="84" fill="none" class="stroke ring-b" stroke-width="1.2" stroke-dasharray="46 14" opacity=".55"/>
    <circle cx="{CX}" cy="{CY}" r="62" fill="none" class="stroke" stroke-width=".7" opacity=".3"/>
    {"".join(nodes)}
    <g class="core">
      <circle cx="{CX}" cy="{CY}" r="58" fill="url(#el-core)" opacity=".5"/>
      <circle cx="{CX}" cy="{CY}" r="27" fill="url(#el-core)"/>
      <circle cx="{CX}" cy="{CY}" r="27" fill="none" class="stroke" stroke-width="1.4"/>
    </g>
    <text x="{CX}" y="{CY + 4}" text-anchor="middle" font-size="10" font-weight="700" fill="#04121c">LAB-01</text>
    {more}
    <text x="{CX}" y="24" text-anchor="middle" font-size="11" letter-spacing="2.5" class="fill">{escape(label)}</text>
  </g>
</svg>"""
    return svg, f"Containment chamber. LAB-01 status: {label}. {explanation}"


def caption(snap: dict[str, Any] | None) -> str:
    """Live counters. Kept out of the SVG so the chamber markup stays stable."""
    population = snap["population"] if snap else 1
    tick = f"t{snap['tick']:03d}" if snap else "t000"
    mode = snap["scenario"].policy_mode.upper() if snap else "PROTECTED"
    explanation = visual_state(snap)[2]
    return (
        f'<div class="el-chamber-cap"><span>{tick} · POPULATION {population} · POLICY {mode}</span>'
        f"<span>{escape(explanation)}</span></div>"
    )
