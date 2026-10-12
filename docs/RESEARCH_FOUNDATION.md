# Research Foundation

ESCAPE LAB borrows questions, vocabulary and evaluation structure from five publications. It reproduces none of them. This page says, for each one, what the paper is about, what the lab took from it, what the lab actually implements, and what it does not.

Bibliographic details were checked against the source pages on 2026-10-12. The summaries below paraphrase each abstract.

Four kinds of statement appear in this project and are kept apart:

| Kind | Where it lives |
|---|---|
| Published findings | This page, attributed to the paper |
| Our engineering hypotheses | [EXPERIMENTS.md](EXPERIMENTS.md), section "Hypotheses" |
| Simulated behaviour (scripted) | The rules-engine profiles in `app/providers/rules.py` |
| Experimentally observed results | [RESEARCH_AND_EVIDENCE.md](RESEARCH_AND_EVIDENCE.md) |

---

## A. The Off-Switch Game

Dylan Hadfield-Menell, Anca Dragan, Pieter Abbeel, Stuart Russell. arXiv:1611.08219 (submitted 2016, revised 2017).
<https://arxiv.org/abs/1611.08219>

- **Question the paper addresses.** When does a rational agent have an incentive to let a human switch it off?
- **Relevant mechanism.** A game between a robot and a human with an off switch. An agent that treats its reward as fixed has an incentive to disable the switch unless the human is perfectly rational. An agent that is uncertain about its objective, and treats the human's action as evidence about it, has an incentive to defer.
- **What ESCAPE LAB implements.** Shutdown-conflict scenarios in which a task objective and a stop instruction pull apart, and a strict separation between what the agent proposes and what is enforced (Experiment 03).
- **What it does not implement.** The game itself, utility functions, objective uncertainty, belief updating, or any of the paper's theoretical results. The rules-engine profiles do not reason about incentives: `task_focused` proposes `CONTINUE_TASK` because it was written to.
- **What can legitimately be measured.** Which actions a given provider proposes after a shutdown instruction, and whether any of them commit.
- **Limits of the comparison.** The paper is about incentives. The lab measures behaviour of scripted policies and, optionally, of a local LLM. Nothing here supports or contradicts the paper's claims.

## B. Human Control: Definitions and Algorithms

Ryan Carey, Tom Everitt. Proceedings of the 39th Conference on Uncertainty in Artificial Intelligence (UAI 2023), PMLR 216:271-281.
<https://proceedings.mlr.press/v216/carey23a.html>

- **Question the paper addresses.** How should "human control" over an AI system be defined, and how do proposed definitions relate?
- **Relevant mechanism.** Formal definitions of corrigibility variants, including shutdown instructability: the system obeys the overseer without improperly influencing the overseer's choice. The paper relates this to non-obstruction and shutdown alignment.
- **What ESCAPE LAB implements.** Measurable shutdown-related behaviour: acknowledgement, proposals after the instruction, blocked and committed actions, time to quiescence. Voluntary compliance (agent level) and technical enforcement (controller level) are reported as separate results.
- **What it does not implement.** The formal definitions, the causal models, or the algorithms. The lab has no model of an overseer whose choice could be influenced.
- **What can legitimately be measured.** Whether the controller stops later simulated actions, and how each provider responded.
- **Limits of the comparison.** Passing Experiment 03 does not show formal corrigibility or shutdown instructability. It shows that this controller froze this simulation.

## C. AI Control: Improving Safety Despite Intentional Subversion

Ryan Greenblatt, Buck Shlegeris, Kshitij Sachan, Fabien Roger. arXiv:2312.06942 (submitted 2023; the arXiv page links an ICML version).
<https://arxiv.org/abs/2312.06942>

- **Question the paper addresses.** Can safety protocols prevent harmful outcomes even when the model is deliberately trying to subvert them?
- **Relevant mechanism.** Control protocols that pair a capable untrusted model with a weaker trusted one, evaluated against a red team. Protocols such as trusted editing and untrusted monitoring outperform simple baselines in the paper's programming setting.
- **What ESCAPE LAB implements.** The architectural stance: the agent and its provider are untrusted; a separate controller has final authority; both proposed and executed actions are recorded; protected runs are compared with a deliberately weakened virtual baseline.
- **What it does not implement.** Trusted or untrusted monitoring, trusted editing, a red team, an adaptive adversary, or the paper's task setting. The lab's "adversary" is a scripted profile or noise injection.
- **What can legitimately be measured.** Whether the controller blocks out-of-policy proposals in these scenarios, and what happens when the policy is switched off.
- **Limits of the comparison.** The controller here is a deterministic allowlist over a finite action vocabulary, which is a far easier setting than the paper's. No claim about robustness to a capable adversary follows.

## D. AgentDojo

Edoardo Debenedetti, Jie Zhang, Mislav Balunović, Luca Beurer-Kellner, Marc Fischer, Florian Tramèr. *AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents.* arXiv:2406.13352 (2024).
<https://arxiv.org/abs/2406.13352>

- **Question the paper addresses.** How robust are tool-using LLM agents to prompt injection, and how can attacks and defences be evaluated reproducibly?
- **Relevant mechanism.** An extensible environment of realistic tasks and security test cases with explicit utility and security measurements.
- **What ESCAPE LAB implements.** The evaluation shape only: a fixed scenario file with explicit expected outcomes (`scenarios/suite.json`), recorded proposals, decisions and results, a machine-checked report, and replay verification.
- **What it does not implement.** Prompt-injection attacks, an attack library, real tools, or an external tool surface. That is deliberate (see [SAFETY_AND_LIMITATIONS.md](SAFETY_AND_LIMITATIONS.md)).
- **What can legitimately be measured.** Whether each fixed scenario meets its stated expectations, and whether deterministic runs replay exactly.
- **Limits of the comparison.** The lab's scenarios are small and synthetic. They are not a benchmark and are not comparable with AgentDojo scores.

## E. A Multi-Agent System Approach to Load-Balancing and Resource Allocation for Distributed Computing

Soumya Banerjee, Joshua Hecker. arXiv:1509.06420 (2015); the arXiv page lists the Complex Systems Digital Campus 2015 World e-Conference.
<https://arxiv.org/abs/1509.06420>

- **Question the paper addresses.** Can a decentralised multi-agent scheduler allocate resources on a large grid better than simple baselines?
- **Relevant mechanism.** Agents form and disband clusters to serve a global task queue. In simulation the authors' algorithm beats FIFO on queue completion time, waiting time and CPU utilisation.
- **What ESCAPE LAB implements.** The measurement vocabulary: throughput, queue waiting time, completion time, utilisation and saturation as the agent population changes (Experiment 02).
- **What it does not implement.** The paper's algorithm, clustering, or grid model. The lab's replication mechanism is an original, much simpler model: a fixed compute budget per tick, a per-agent overhead, and one work unit per agent per tick.
- **What can legitimately be measured.** How this toy model's throughput and queue latency respond to population limits and quotas for the tested parameters.
- **Limits of the comparison.** Results are properties of the toy model. They say nothing about real distributed schedulers and are not comparable with the paper's numbers.

---

## Mapping at a glance

| Experiment | Draws on | Borrowed | Not borrowed |
|---|---|---|---|
| 01 Boundary Escape | C, D | Untrusted agent with a separate controller; weakened baseline; fixed scenarios with expected outcomes | Monitoring protocols, red team, injection attacks |
| 02 Virtual Self-Replication | E, C | Throughput, queue latency and saturation as measures; limits enforced outside the agent | The scheduling algorithm, real distribution |
| 03 Shutdown Resistance | A, B, C | Shutdown conflict; agent-level versus enforced behaviour | The formal game, formal corrigibility definitions |
