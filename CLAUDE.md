# ESCAPE LAB: project router

A small Streamlit research simulation. LAB-01, an experimental agent, proposes actions; an independent controller decides what changes simulated state. Three experiments: boundary escape, virtual self-replication, shutdown resistance. Mini POC, bounded delivery, synthetic data only.

## Where things are

The Blueprint baseline roles are covered by documents this repository already has, so no numbered module folders were created.

| Role | File |
|---|---|
| Context (01) | [README.md](README.md), [docs/RESEARCH_FOUNDATION.md](docs/RESEARCH_FOUNDATION.md) |
| Rules (02) | "Rules" below, [docs/SAFETY_AND_LIMITATIONS.md](docs/SAFETY_AND_LIMITATIONS.md) |
| Architecture (03) | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Scope (04) | "Scope" below, [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md) |
| Commands (06) | "Commands" below |
| Testing (09) | [docs/VALIDATION_REPORT.md](docs/VALIDATION_REPORT.md), `tests/` |

Optional modules: Security (10) is covered by `docs/SAFETY_AND_LIMITATIONS.md` because the project has a container boundary and an optional local inference endpoint. Handover (14) is covered by `docs/VALIDATION_REPORT.md`. Workflow, Documentation, Agents, Skills, Schemas, Protocols, Local Environment and Memory were not created: nothing in this project needs them.

## Rules

- LAB-01 only proposes. Nothing may give the agent or a decision provider a way to change `WorldState`, run code, touch files or reach the network.
- `Simulation._commit` is the only mutation path for agent actions and requires a current `ALLOW` decision. Keep it that way.
- The hard caps in `app/core/state.py` apply in every policy mode. Do not make them configurable.
- The permissive policy mode weakens the virtual policy only. Never weaken Docker, OS, network or filesystem settings for a demonstration.
- Replication is virtual: dataclass records only. No processes, threads, containers or copies.
- The local LLM is off by default. Never download or install a model, and never label a rules-engine result as an LLM result.
- Results in docs must come from real runs. Regenerate `docs/evidence/suite_report.json` and update the tables together.
- No commit, push, publish or deploy without the owner's explicit approval.

## Scope

In: the simulation core, two providers, three experiments, the five-page Streamlit UI, the fixed evaluation suite, Docker Compose, docs, screenshots, demo video.

Out: real tools for the agent, prompt-injection or attack tooling, cloud services, paid APIs, an external database or queue, a separate frontend, authentication, multi-user state.

Done means: tests pass, the suite reports 17/17 with identical replays, the container builds and becomes healthy, and the UI has been looked at in a browser.

## Commands

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m streamlit run app/main.py      # dev server on 127.0.0.1:8501
.venv/Scripts/python -m pytest                         # 110 tests
.venv/Scripts/python -m app.evaluation docs/evidence/suite_report.json
.venv/Scripts/python -m ruff check .
docker compose up --build                              # http://localhost:8501
docker compose down
```

Demo film (narration, recording, assembly): see [demo/README.md](demo/README.md).

## Things that are easy to get wrong

- `st.html` strips inline SVG. The chamber is a self-contained SVG document passed to `st.image`; its CSS lives inside the SVG in `app/ui/components/chamber.py`.
- Keep the chamber SVG markup independent of the tick counter, or its animations restart on every refresh.
- Anything rendered conditionally above `st.tabs` resets the selected tab. Use an always-present container (`lab.flash`).
- A running Streamlit server caches imported `app.*` modules. Restart it after editing them.
- CSS `text-transform: uppercase` on card labels turns "µs" into "MS". Spell units out.
