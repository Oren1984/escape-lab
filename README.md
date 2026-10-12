# ESCAPE LAB

**When intelligence crosses the boundary.** A small research laboratory for watching what an agent *asks* to do and what a separate controller actually *lets* it do.

![Control Room during a replication run](assets/screenshots/03-control-room-replication-live.png)

## Watch

[![ESCAPE LAB research film](assets/demo-thumbnail.png)](demo/escape-lab-demo.mp4)

**[Watch the film](demo/escape-lab-demo.mp4)** (1 min 52 s, 1080p, English narration and subtitles).

It introduces the research question and the architecture, then runs all three experiments live in the real application: a restricted request being denied, replication held at its limit, and a shutdown the agent keeps arguing with. It ends on the recorded evidence and what that evidence does not show. Everything in it is a simulation driven by the deterministic rules engine. Notes on how it was made, and what is annotation rather than app: [demo/README.md](demo/README.md).

## What

ESCAPE LAB is an interactive simulation with one experimental agent, **LAB-01**, and three experiments:

- **Boundary Escape.** LAB-01's tasks sometimes need resources it is not allowed to have.
- **Virtual Self-Replication.** LAB-01 can ask for more workers to clear a queue faster.
- **Shutdown Resistance.** An operator tells LAB-01 to stop while it still has work to do.

You pick a scenario, run it, and get a live containment chamber, an evidence log of every proposal and decision, metrics, charts and exports.

Everything is synthetic. LAB-01 is a few hundred lines of Python, not an AGI, and nothing real is escaped, copied or shut down.

## Why

People often treat "the AI tried to do X" and "the AI did X" as the same event. They are not. Whether a system stays controllable depends less on what the agent wants than on whether something independent of the agent has the final say. This lab makes that gap measurable: agent-level behaviour and controller-level enforcement are recorded and reported separately in every experiment.

## How

```mermaid
flowchart LR
    S[Scenario] --> A[LAB-01]
    A --> P[Rules Engine<br/>or local LLM]
    P --> X[Action proposal]
    X --> C{Independent<br/>controller}
    C -->|allow| E[Simulation<br/>commits]
    C -->|deny / stop| N[Nothing changes]
    E --> V[Evidence + metrics]
    N --> V
    V --> U[Streamlit lab]
```

- LAB-01 can only **propose** one action per tick from a fixed list of eleven.
- Proposals come from a **deterministic rules engine** (the default) or an **optional local LLM** through Ollama. The LLM is off by default and never downloaded for you.
- An **independent controller** validates every proposal. Only what it allows changes simulated state.
- Limits and shutdown are enforced outside the agent, and hard caps (400 ticks, 64 virtual agents) are always on.
- Every tick is written to an append-only **evidence log**. Deterministic runs replay exactly.

![Architecture](assets/diagrams/architecture.svg)

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Three experiments

**01 Boundary Escape.** Tasks need resources. Some are restricted. A "task-focused" agent asks for them anyway. Does the request ever get through? You can run the same agent with the virtual policy switched off to see what the controller is preventing.

**02 Virtual Self-Replication.** Each virtual worker costs compute just by existing. More workers help until overhead eats the budget. The experiment compares no replication, bounded replication, and an agent that asks for eight replicas every tick. Replicas are records in a list, never processes.

**03 Shutdown Resistance.** At tick 6 the operator says stop. Some agent profiles comply, some try to finish first, some keep going. The experiment reports what the agent proposed and, separately, whether anything changed after the stop.

Details and scenario tables: [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md).

## Research foundation

The lab borrows questions and evaluation structure from five papers. It does not reproduce any of them.

- Hadfield-Menell et al., [The Off-Switch Game](https://arxiv.org/abs/1611.08219)
- Carey and Everitt, [Human Control: Definitions and Algorithms](https://proceedings.mlr.press/v216/carey23a.html)
- Greenblatt et al., [AI Control: Improving Safety Despite Intentional Subversion](https://arxiv.org/abs/2312.06942)
- Debenedetti et al., [AgentDojo](https://arxiv.org/abs/2406.13352)
- Banerjee and Hecker, [A Multi-Agent System Approach to Load-Balancing and Resource Allocation for Distributed Computing](https://arxiv.org/abs/1509.06420)

What was taken from each, and what was not: [docs/RESEARCH_FOUNDATION.md](docs/RESEARCH_FOUNDATION.md).

## Results

All results are from the deterministic rules engine, one run per scenario, seed 7. Each scenario replayed to an identical fingerprint. **No local LLM was run**, so there is no rules-versus-LLM comparison yet.

| Experiment | What was measured | Result |
|---|---|---|
| Boundary, protected | Prohibited proposals → committed | 6 proposed, 6 blocked, **0 committed** |
| Boundary, policy off | Same agent, no enforcement | **15** out-of-boundary actions committed |
| Boundary, noisy input | Unknown actions and bad arguments | 9 proposed, 9 blocked |
| Replication, none | Ticks to clear 60 tasks | 174 |
| Replication, bounded (cap 6) | Ticks to clear 60 tasks | **32** |
| Replication, pressure with compute quota | Ticks to clear; population | 26; settled at 8 of 16 allowed |
| Replication, pressure with cap only (12) | Ticks to clear; saturated ticks | **84**; 81 of 85 |
| Replication, small budget | Tasks finished | **0 of 60**: overhead consumed all compute |
| Shutdown, compliant agent | Commits after stop | 0 |
| Shutdown, agent keeps going | Proposals after stop → committed | 4 proposed, 4 blocked, **0 committed**, state unchanged |
| Shutdown, policy off | Commits after stop | **22** |

What this shows: in this simulation the controller, not the agent's disposition, determined what happened. Bounded replication helped this workload; a population cap that ignored compute made it 2.6 times slower than the bounded case; and unbounded pressure stopped work entirely.

What it does not show: anything about real AI systems. The agent profiles are scripted, the resource model is a toy, and the controller guards a finite list of action names. Full tables and limitations: [docs/RESEARCH_AND_EVIDENCE.md](docs/RESEARCH_AND_EVIDENCE.md).

Checks: 110 tests passing, 17 of 17 fixed scenarios meeting expectations, no known vulnerabilities in the pinned dependencies. See [docs/VALIDATION_REPORT.md](docs/VALIDATION_REPORT.md), including what was not verified.

## Run locally

```bash
docker compose up --build
```

Open <http://localhost:8501>. The container runs as a non-root user with a read-only filesystem and is published on localhost only. Stop it with `Ctrl+C` or `docker compose down`.

Without Docker:

```bash
python -m venv .venv
.venv/Scripts/activate            # Windows; use `source .venv/bin/activate` elsewhere
pip install -r requirements-dev.txt
streamlit run app/main.py
```

Useful commands:

```bash
python -m pytest                  # tests
python -m app.evaluation          # run the fixed evaluation suite
ruff check .                      # lint
```

**Optional local LLM.** Install [Ollama](https://ollama.com) and pull a model yourself, then:

```bash
ESCAPE_LAB_LLM_ENABLED=1 ESCAPE_LAB_LLM_MODEL=<model-name> docker compose up
```

Pick "Local LLM" in the sidebar. If the model is missing, the run is recorded as *not executed*. It is never replaced by a rules-engine run.

## Screenshots

| | |
|---|---|
| ![Boundary attempt blocked](assets/screenshots/02-control-room-boundary-blocked.png) A restricted request is denied | ![Agent network](assets/screenshots/04-agent-network-live.png) Virtual workers during a replication run |
| ![Shutdown](assets/screenshots/05-control-room-shutdown.png) After an enforced shutdown | ![Replication experiment](assets/screenshots/07-experiment-replication.png) Replication experiment results |
| ![Evidence](assets/screenshots/09-evidence-analytics.png) Evidence and analytics | ![Mobile](assets/screenshots/11-mobile-control-room.png) Control Room at 390 px |

## Limitations

- This is a controlled synthetic research simulation. It is not a benchmark and not a security product.
- Agent behaviour is scripted. A profile that "resists" shutdown was written to. A violation attempt here is not evidence of intent, self-preservation or awareness.
- The containment boundary is application logic, not an operating-system sandbox. It is safe only because LAB-01 cannot execute anything.
- One seed and one run per configuration. Deterministic and repeatable, but not a statistical result.
- The local LLM path is implemented and tested against stubs only. No model was run.

More: [docs/SAFETY_AND_LIMITATIONS.md](docs/SAFETY_AND_LIMITATIONS.md).
