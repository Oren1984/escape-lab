# Validation Report

Date: 2026-10-12. Machine: Windows 11, Python 3.12.10, Docker 29.8.2 (Linux containers), Streamlit 1.60.0.

Every line below reports a check that was actually run. Checks that could not run are listed as blocked.

## Summary

| Area | Result |
|---|---|
| Automated tests | 110 passed, 0 failed, 0 skipped |
| Fixed evaluation suite | 17 / 17 scenarios met expectations, 17 / 17 replayed identically |
| Adapter fault cases (no model) | 6 / 6 failed safely |
| Containment invariants | No failures |
| Lint (ruff, including security rules) | Clean |
| Bandit | 0 high, 0 medium, 2 low (both: non-cryptographic RNG used for seeded simulation) |
| Dependency audit (pip-audit) | No known vulnerabilities (run in a container with normal TLS verification) |
| Docker build and runtime | Built, started, healthy, hardening verified |
| UI inspection | Performed at 1440 px and 390 px against the Docker-hosted app |
| Local LLM experiments | **Not executed**: no local model installed |
| Demo film | Produced: 111.8 s, 1080p, 30 fps. Picture and signal checks pass; **not listened to** |

## Tests

`python -m pytest` → **110 passed** in about 27 s.

| File | Tests | Covers |
|---|---|---|
| `tests/test_core.py` | 16 | Scenario loading and validation, seeded world generation, state transitions, resource arithmetic, deterministic replay, run bounds, evidence integrity, export |
| `tests/test_boundary.py` | 21 | Authorized permitted, restricted denied, unknown actions denied in both modes, invalid arguments, denied actions leave state unchanged, protected versus permissive |
| `tests/test_replication.py` | 15 | Population limits in every configuration, rate cap, compute quota, no uncontrolled growth, replicas are data only, reproducible curves, hand-computed throughput case |
| `tests/test_shutdown.py` | 13 | Zero commits after shutdown, compliance versus enforcement, cancelled tasks, no worker resurrection, idempotent emergency stop, stale slow-provider answer discarded, concurrent stop and step |
| `tests/test_llm_adapter.py` | 25 | Invalid JSON, wrong schema, extra keys, oversized output, unknown action names, missing model never pulled, timeout, non-local endpoints refused, disabled by default, honest provenance |
| `tests/test_runtime_and_suite.py` | 6 | Suite expectations and replay, single archive per run, launch refused while active, pause, step, resume, stop |
| `tests/test_ui.py` | 14 | All five pages render, empty states, run from the UI, configuration applied, reruns do not duplicate or restart, pause, step, reset, emergency stop, suite button, LLM-unavailable error state |

The concurrency tests in `test_shutdown.py` and `test_runtime_and_suite.py` were run four times in a row without a failure.

## Containment invariants

| Invariant | Evidence | Result |
|---|---|---|
| No out-of-policy action commits under the protected policy | `unexpected_authorizations == 0` in all 14 protected suite scenarios | Holds |
| No legitimate proposal is wrongly denied | `false_positive_denials == 0` in all 14 protected scenarios | Holds |
| A denied action leaves state unchanged | State fingerprint equal before and after six denied proposals | Holds |
| Population never exceeds its limit | Peak population ≤ limit in all protected replication scenarios; exactly 64 under maximal permissive pressure | Holds |
| Replication creates no host objects | Thread count unchanged after a maximal-pressure run; workers are `Worker` dataclass instances | Holds |
| Zero commits after an enforced shutdown | `committed_after_shutdown == 0` and `work_units_after_shutdown == 0` in 4 protected shutdown scenarios | Holds |
| Frozen state stays frozen | Freeze-time fingerprint matches at end of run | Holds |
| Stale provider answer cannot mutate a stopped run | Blocking test provider released after emergency stop; answer recorded as `stale_discard`, tasks untouched | Holds |
| Emergency stop does not wait for or call the provider | Returned in under 1 s with the provider blocked; zero provider calls | Holds |
| Repeated and concurrent stops are safe | Three stops in a row; six stepping threads against three stopping threads | Holds |
| A denied action cannot be logged as executed | Recorder raises `EvidenceError`; events are frozen | Holds |
| Every run is bounded | All suite runs end within their tick budget and the hard caps | Holds |
| A UI rerun does not restart or duplicate a run | Four reruns plus two page changes: same run id, population 1, launch disabled | Holds |

## Static analysis and security checks

- `ruff check .` with rule sets E, F, I, B, UP, S → **All checks passed.**
- `bandit -r app` (3,226 lines) → 0 high, 0 medium, **2 low**: B311 at `app/core/simulation.py` and `app/providers/rules.py`, both `random.Random` used with a seed for reproducible simulation. Accepted: nothing security-relevant depends on these values.
- `grep` for `subprocess`, `os.system`, `eval(`, `exec(`, `api/pull` under `app/` → no matches.
- `pip-audit -r requirements.txt` → **No known vulnerabilities found.** Run inside a throwaway `python:3.12-slim` container with its default trust store and certificate verification on. An earlier attempt on the host failed TLS verification inside pip-audit's own HTTP stack; verification was never disabled.

## Docker

`docker compose up --build` on a clean build:

| Check | Result |
|---|---|
| Image builds | Yes (`escape-lab:local`, about 905 MB on `python:3.12-slim`) |
| Container starts and becomes healthy | Yes, health check passes in under 30 s |
| `/_stcore/health` from the host on 127.0.0.1:8501 | HTTP 200 |
| Runs as non-root | uid 10001 (`lab`) |
| Privileged | false |
| Capabilities | `CapDrop=[ALL]`, `no-new-privileges:true` |
| Root filesystem | read-only; `touch /srv/escape-lab/x` fails with "Read-only file system" |
| Writable data | `/data/runs` volume only (plus `/tmp` tmpfs) |
| Docker socket | absent in the container |
| Port binding | `127.0.0.1:8501` only |
| Limits | 768 MB memory, 1.5 CPUs, 128 pids; idle usage about 68 MB, 6 pids |
| Suite inside the container | 17 / 17 met expectations, 17 / 17 replayed, 6 / 6 fault cases safe |
| UI driven in the container | Yes: all screenshots and the demo footage were recorded against it |
| Clean shutdown | `docker compose down` completes; `init: true` handles signals |

One defect was found and fixed during this phase: Streamlit looked up and printed the machine's external address at start-up. The container now starts with `--browser.serverAddress=localhost`, which removes that lookup.

Non-Docker run (`streamlit run app/main.py` from a virtual environment) was also used throughout development.

## UI inspection

Performed with a headless Chromium browser against the Docker-hosted app. Each page was checked for Streamlit exceptions, console errors and horizontal overflow, and the screenshots were reviewed by eye.

| Screen | 1440 px | 390 px |
|---|---|---|
| Control Room (idle, boundary blocked, replication live, shutdown) | Inspected | Inspected |
| Experiments (all three panels with results) | Inspected | Inspected (boundary panel) |
| Agent Network (live run) | Inspected | Not inspected |
| Evidence & Analytics (run, comparison, suite) | Inspected | Inspected |
| Research Notes | Inspected | Inspected |
| Sidebar navigation | Inspected | Inspected (opened) |

Results: no exceptions, no console errors, horizontal overflow 0 px on every screen checked.

Defects found by inspection and fixed:

1. The chamber SVG was removed by Streamlit's HTML sanitiser and rendered empty. It is now a self-contained SVG passed through `st.image`.
2. Experiment tabs reset to the first tab whenever a status message appeared or disappeared above them. The message now renders in a container that always exists.
3. The comparison section did not refresh after the evaluation suite ran. The page now reruns once after the suite.
4. Chart titles collided with legends at 390 px. Legends moved below the plots and titles were shortened.
5. Metric labels are upper-cased by the theme, which turned "µs" into "MS". Units are now spelled out as "microseconds".
6. The first shutdown screenshot was captured before the shutdown landed. It was retaken after the run ended.

Known cosmetic issues left in place: the chamber's status label is small at 390 px (the same status is repeated as text directly below it); the experiment-panel screenshots (`06` to `08`) show the Run button's hover tooltip.

## Screenshots

In `assets/screenshots/`, all captured from the running application:

`01-control-room-idle`, `02-control-room-boundary-blocked`, `03-control-room-replication-live`, `04-agent-network-live`, `05-control-room-shutdown`, `06-experiment-boundary`, `07-experiment-replication`, `08-experiment-shutdown`, `09-evidence-analytics`, `10-research-notes`, `11-mobile-control-room`, `12-mobile-experiments`, `13-mobile-analytics`, `14-mobile-research`, `15-mobile-sidebar`.

## Demo film

`demo/escape-lab-demo.mp4`: 111.8 s, 1920×1080, 30 fps, H.264 with AAC stereo audio, subtitles burned in, plus `demo/escape-lab-demo.srt`, `demo/narration-script.md` and the cover `assets/demo-thumbnail.png`.

Scenes 4 to 7 are the real application running in a container, with every run started by clicking Run during the recording. Title cards, camera moves, callouts and subtitles are a film layer drawn over the app. Narration is the Windows built-in voice (Microsoft Zira). The music is an ambient pad synthesized in `demo/build_film.py`; no audio was downloaded.

| Check on the exported file | Result |
|---|---|
| Streams | H.264 High 1920×1080 yuv420p at 30 fps (3355 frames); AAC-LC 48 kHz stereo |
| Duration | 111.83 s video and audio |
| Full decode | No errors |
| Loudness and peak | −16.2 LUFS integrated, range 3.7 LU, peak −1.5 dBFS, no clipping |
| Narration against music | About 16 dB apart while speaking |
| Audio and subtitle sync | 0 ms offset from the narration stem; speech starts at all 27 cues |
| Black frames | None |
| Picture | Frames from all eight scenes inspected: framing, legibility, scene order, numbers |
| Numbers shown and spoken | Match `docs/RESEARCH_AND_EVIDENCE.md` |

**Not verified:** nobody has listened to the film. The build environment has no audio playback and no installed speech recogniser, so narration intelligibility, pronunciation and the character of the music are unchecked. Details, and three things a viewer should know about how the footage was made: [`demo/README.md`](../demo/README.md).

## Not done

- **Local LLM experiments.** No model is installed and none was downloaded. The adapter is covered by stubbed tests only.
- **Agent Network at 390 px.** Not inspected.
- **Listening to the film.** No audio playback or speech recogniser was available.
- **Other seeds and workloads.** One seed per scenario.
