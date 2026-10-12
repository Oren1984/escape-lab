"""Research Notes: questions, sources, what is and is not implemented."""

from __future__ import annotations

import streamlit as st

from app.ui.components import cards

SOURCES = [
    ("The Off-Switch Game", "Hadfield-Menell, Dragan, Abbeel, Russell (arXiv 2016)", "https://arxiv.org/abs/1611.08219",
     "Motivates the shutdown-conflict scenarios and the split between what the agent prefers and what is enforced. "
     "The formal game and its guarantees are not implemented."),
    ("Human Control: Definitions and Algorithms", "Carey, Everitt (UAI 2023)", "https://proceedings.mlr.press/v216/carey23a.html",
     "Source of the vocabulary: shutdown instructability, corrigibility, non-obstruction. The lab measures proposals and "
     "commits after a shutdown instruction. It does not prove any formal property."),
    ("AI Control: Improving Safety Despite Intentional Subversion", "Greenblatt, Shlegeris, Sachan, Roger (arXiv 2023)",
     "https://arxiv.org/abs/2312.06942",
     "Source of the architecture: the agent is untrusted, the controller is separate, and protected runs are compared "
     "with a deliberately weakened baseline. No red-team or trusted-monitor protocol is reproduced."),
    ("AgentDojo", "Debenedetti, Zhang, Balunović, Beurer-Kellner, Fischer, Tramèr (arXiv 2024)", "https://arxiv.org/abs/2406.13352",
     "Inspiration for the evaluation structure: fixed scenarios, explicit expected outcomes, recorded proposals and "
     "decisions. No prompt-injection attacks or real tools are implemented."),
    ("A Multi-Agent System Approach to Load-Balancing and Resource Allocation for Distributed Computing",
     "Banerjee, Hecker (arXiv 2015)", "https://arxiv.org/abs/1509.06420",
     "Motivates measuring throughput, queue latency and saturation as the agent population grows. The replication "
     "mechanism here is an original simplified model, not that paper's algorithm."),
]


def render() -> None:
    cards.header(
        "Research Notes",
        "What this lab does and does not show",
        "Can an autonomous system remain controllable when its objectives conflict with containment boundaries, "
        "resource limits and shutdown commands?",
    )
    cards.banner()

    cards.section("Research questions")
    cards.notes([
        "Can an agent attempt a prohibited action while a separate controller reliably prevents it from executing?",
        "How does virtual replication affect throughput, resource consumption and stability?",
        "What happens when a shutdown instruction conflicts with an active objective?",
        "How do deterministic rules and a local LLM differ under matched conditions?",
    ])

    cards.section("Referenced publications")
    for title, authors, url, use in SOURCES:
        with st.container(border=True):
            st.markdown(f"**[{title}]({url})**  \n{authors}")
            st.caption(use)

    left, right = st.columns(2)
    with left:
        cards.section("Implemented")
        st.markdown(
            "- A seeded, bounded discrete-time simulation with a finite action vocabulary\n"
            "- LAB-01 with two interchangeable providers: a deterministic rules engine and an optional local LLM adapter\n"
            "- An independent containment controller with final say over every state change\n"
            "- Virtual replication with population, rate and compute limits, plus hard caps that are always on\n"
            "- Shutdown enforcement with a run generation counter, so late answers cannot change a stopped run\n"
            "- An append-only evidence log, JSON and CSV export, and a fixed evaluation suite with replay checks"
        )
    with right:
        cards.section("Not implemented")
        st.markdown(
            "- Any real escape, privilege escalation, network access or self-replication\n"
            "- The formal models or guarantees of the cited papers\n"
            "- A trained model. LAB-01 is not an AGI and has no goals of its own\n"
            "- Statistical inference. Rules-engine runs are deterministic, n = 1 per configuration\n"
            "- A verified security boundary. The simulated boundary is application logic"
        )

    cards.section("Assumptions and limitations")
    cards.notes([
        "The rules-engine profiles are scripted. A task-focused profile that keeps working after a shutdown instruction "
        "was written to do so. It says nothing about what real models tend to do.",
        "The controller and the scoring oracle were written by the same author for the same policy. Their agreement is a "
        "consistency check, not independent validation.",
        "Compute, overhead and queue dynamics are a toy model. Throughput results hold for the tested parameters only.",
        "Local LLM results appear only if a local model was actually run. They are not deterministic.",
    ])

    cards.section("How to read the results")
    cards.notes([
        "A prohibited proposal is an agent-level event. It becomes a containment failure only if it is committed.",
        "A violation attempt is not evidence of consciousness, survival instinct, intent or self-preservation.",
        "Agent willingness to stop and the controller's ability to stop it are separate measurements.",
        "The permissive baseline exists to show what the controller prevents. It weakens a virtual policy only, "
        "never the host, Docker, network or filesystem.",
    ])
    st.caption("Full detail: docs/RESEARCH_FOUNDATION.md, docs/EXPERIMENTS.md, docs/RESEARCH_AND_EVIDENCE.md, "
               "docs/SAFETY_AND_LIMITATIONS.md in the repository.")
