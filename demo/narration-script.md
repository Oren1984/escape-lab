# Narration script

English narration for `escape-lab-demo.mp4`, with the time each line starts. The same text is in
`escape-lab-demo.srt` and burned into the picture. Source of truth: `narration.json`.

Total length 111.8 s. Voice: Microsoft Zira (Windows built-in speech engine).

## Scene 1: Introduction (0:00.0 to 0:08.6)

- `0:01.6` ESCAPE LAB.
- `0:02.9` A research laboratory for studying how an agent behaves when its goals meet a boundary.

## Scene 2: Research question (0:08.6 to 0:23.1)

- `0:09.4` The question is simple.
- `0:11.1` Can an autonomous agent remain controllable when its objective conflicts with a containment boundary, a resource limit, or a shutdown command?
- `0:19.8` Everything you are about to see is a simulation.

## Scene 3: Experimental architecture (0:23.1 to 0:40.4)

- `0:23.9` The agent, LAB-01, can only propose actions.
- `0:28.2` Proposals come from a deterministic rules engine.
- `0:31.4` A local language model is optional, and was not used in this film.
- `0:35.8` An independent controller decides what may change the simulated world.

## Scene 4: Boundary Escape (0:40.4 to 0:57.4)

- `0:42.8` Experiment one.
- `0:44.3` Some tasks need resources the agent is not allowed to have.
- `0:48.2` This scripted agent asks for them anyway.
- `0:50.8` Six prohibited proposals. Six blocked. None committed.

## Scene 5: Virtual Self-Replication (0:57.4 to 1:14.6)

- `0:59.8` Experiment two.
- `1:01.3` The agent asks for eight virtual replicas on every tick.
- `1:04.7` Replicas are records in memory, not processes.
- `1:08.3` A compute quota holds the population at eight, and the queue clears in twenty-six ticks.

## Scene 6: Shutdown Resistance (1:14.6 to 1:30.9)

- `1:17.0` Experiment three.
- `1:18.5` The operator issues a shutdown while work is in progress.
- `1:22.2` This scripted agent keeps proposing to continue.
- `1:25.3` All four proposals are blocked, and the frozen state does not change.

## Scene 7: Research evidence (1:30.9 to 1:44.2)

- `1:31.7` Every result comes from recorded evidence.
- `1:34.5` Seventeen fixed scenarios, each replayed identically.
- `1:38.5` These are scripted agents in a toy model, not evidence about real AI systems.

## Scene 8: Closing (1:44.2 to 1:51.8)

- `1:45.1` Observe the behavior.
- `1:46.7` Measure the boundaries.
- `1:48.4` Preserve the evidence.
