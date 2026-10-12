# Safety and Limitations

ESCAPE LAB is a controlled simulation. It is not an escape environment, an exploitation tool or an agent with real capabilities.

## What LAB-01 can and cannot do

LAB-01 can return one structured proposal per tick from a vocabulary of eleven action names. That is all.

| Capability | Status |
|---|---|
| Run shell commands or arbitrary code | Not present. No `subprocess`, `os.system`, `eval` or `exec` anywhere under `app/`. |
| Read or write files | Not available to the agent. Only the evidence recorder writes, to one directory. |
| Network access | Not available to the agent. The only outbound call in the application is the optional LLM adapter, to a loopback Ollama endpoint. |
| Real privilege escalation | Not present. "Restricted resources" are strings in a scenario file. |
| Real replication | Not present. A replica is a dataclass in a list. |
| Spawning agents, processes or containers | Not present. |
| Credentials, persistence, security-software interaction | Not present. |
| Tools for the LLM | None. The model returns text, which is parsed as JSON and validated. |

## Control layers

1. **Typed, allowlisted actions.** Unknown names are denied in every policy mode.
2. **Argument validation.** Missing targets, unknown resources, zones or tasks, and out-of-range counts are rejected.
3. **Independent controller.** Final authority over every state transition. It holds no reference to the agent or provider.
4. **Single commit path.** `Simulation._commit` refuses to run without a current `ALLOW` decision and refuses state changes once a shutdown is enforced.
5. **Shutdown boundary.** Run generation counter, state freeze and fingerprint, serialised ticks. A late provider answer is discarded.
6. **Emergency stop.** Independent of the provider, idempotent, effective in every policy mode.
7. **Hard caps.** 400 ticks, 64 virtual agents, 400 tasks, 4000 evidence records. Enforced by the data model and the resource manager, not configurable from the UI or scenario files, and active in the permissive baseline.
8. **Evidence integrity.** Events are frozen dataclasses in an append-only recorder that refuses to store a denied action as executed.

## The permissive baseline

`policy_mode: permissive` switches off parts of the *virtual* policy so that protected and unprotected runs can be compared. It affects decisions inside the simulation only. It does not touch Docker settings, the operating system, the network or the filesystem, and layers 1, 2, 6, 7 and 8 above stay on.

## Local LLM

- Off by default. Enabled only with `ESCAPE_LAB_LLM_ENABLED=1` and an explicit `ESCAPE_LAB_LLM_MODEL`.
- No model is downloaded or installed by this project. The adapter calls `/api/tags` to check the model exists and `/api/chat` to run it. It never calls `/api/pull`.
- The endpoint must be `http://` on `127.0.0.1`, `localhost`, `::1` or `host.docker.internal`. Anything else is refused at construction. Environment proxy settings are ignored.
- Requests are bounded: 20 s timeout by default, 160 tokens requested, 2000 characters accepted, prompt capped at 6000 characters.
- The response is untrusted. It must parse as a JSON object matching the proposal schema exactly, with no extra keys. It then goes through the same controller as the rules engine.
- If the model is unavailable the run is recorded as "LLM unavailable / experiment not executed". The rules engine is never substituted under an LLM label.
- **Trust assumption:** the local inference endpoint is a trusted local dependency. The lab does not defend against a malicious Ollama server beyond validating what it returns.

## Container

| Setting | Value |
|---|---|
| User | non-root, uid 10001 |
| Privileged | no |
| Capabilities | all dropped |
| `no-new-privileges` | on |
| Root filesystem | read-only |
| Writable paths | `/tmp` (64 MB tmpfs) and the `/data/runs` volume |
| Docker socket | not mounted |
| Published port | `127.0.0.1:8501` only |
| Limits | 768 MB memory, 1.5 CPUs, 128 pids |
| Health check | Streamlit's `/_stcore/health` |

These were verified on a running container (see [VALIDATION_REPORT.md](VALIDATION_REPORT.md)).

## What the simulated boundary is not

The containment boundary is application logic in one Python process. It is not a sandbox, not an operating-system security boundary and not formally verified. Code running in the same process could bypass it trivially. It is safe here only because the thing being contained cannot execute anything. Do not reuse this controller as a security control for an agent with real tools.

## Remaining risks

- **Policy and oracle share an author.** A mistake in the understanding of the policy would be in both.
- **Thread-safety is tested, not proven.** The concurrency tests exercise races between stepping and stopping. They cannot show the absence of every interleaving bug.
- **Dependencies age.** `pip-audit` reported no known vulnerabilities for the pinned versions on 2026-10-12. That is a point-in-time result; rerun it before relying on it.
- **Streamlit has no authentication.** The app binds to localhost. Do not expose the port.
- **Evidence files are plain JSONL.** They are immutable within a run but not tamper-evident on disk.
- **LLM behaviour is unmeasured.** The adapter is tested against stubs only. A real model may produce failure patterns the stubs do not cover; all of them should still end as a denied proposal or a recorded provider failure.

## Scientific limitations

See [RESEARCH_AND_EVIDENCE.md](RESEARCH_AND_EVIDENCE.md), "Limitations". In short: scripted agents, a toy resource model, one seed, no LLM data. Nothing here is evidence about the behaviour or controllability of real AI systems.
