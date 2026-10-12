"""Build the ESCAPE LAB research film from narration, recorded footage and a synthesized music bed.

    python demo/build_film.py timeline   # sentence timings from the narration WAVs
    python demo/build_film.py audio      # narration + original ambient bed -> build/mix.wav
    python demo/build_film.py assemble   # recorded frames + mix -> MP4, SRT

Order: narrate.ps1, timeline, record.mjs, audio, assemble. See demo/README.md.
Needs numpy, plus ffmpeg and ffprobe on PATH. Nothing is downloaded.
"""

from __future__ import annotations

import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

DEMO = Path(__file__).resolve().parent
BUILD = DEMO / "build"
RATE = 44100
FPS = 30
OUTPUT = DEMO / "escape-lab-demo.mp4"


# -- narration timeline ------------------------------------------------------


def read_voice(path: Path) -> np.ndarray:
    """Mono float samples with leading and trailing silence trimmed."""
    with wave.open(str(path), "rb") as wav:
        if wav.getframerate() != RATE or wav.getsampwidth() != 2 or wav.getnchannels() != 1:
            raise ValueError(f"{path.name}: expected 44.1 kHz 16-bit mono")
        samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16).astype(np.float64) / 32768
    loud = np.flatnonzero(np.abs(samples) > 0.01)
    pad = int(0.03 * RATE)
    return samples[max(0, loud[0] - pad) : loud[-1] + pad]


def timeline() -> dict:
    script = json.loads((DEMO / "narration.json").read_text(encoding="utf-8"))
    gap = script["pause_between_sentences"]
    scenes, clock = [], 0.0
    for scene in script["scenes"]:
        cursor, sentences = scene["lead"], []
        for i, sentence in enumerate(scene["sentences"], start=1):
            length = len(read_voice(BUILD / "voice" / f"{scene['id']}_{i}.wav")) / RATE
            sentences.append({"text": sentence["text"], "start": round(cursor, 3), "end": round(cursor + length, 3),
                              "file": f"{scene['id']}_{i}.wav"})
            cursor += length + gap
        duration = round(cursor - gap + scene["tail"], 3)
        scenes.append({"id": scene["id"], "title": scene["title"], "offset": round(clock, 3),
                       "duration": duration, "sentences": sentences})
        clock += duration
    result = {"total": round(clock, 3), "scenes": scenes}
    (BUILD / "timeline.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    for scene in scenes:
        print(f"{scene['id']}  {scene['offset']:7.2f}s  +{scene['duration']:6.2f}s  {scene['title']}")
    print(f"total {clock:.2f}s")
    return result


# -- audio -------------------------------------------------------------------


def smooth(signal: np.ndarray, seconds: float) -> np.ndarray:
    """Centred moving average, computed with a running sum."""
    width = max(1, int(seconds * RATE))
    padded = np.concatenate((np.zeros(width // 2 + 1), signal, np.zeros(width - width // 2)))
    total = np.cumsum(padded)
    return (total[width:] - total[:-width])[: len(signal)] / width


def ambient_bed(seconds: float) -> np.ndarray:
    """An original ambient pad, synthesized here. Stereo, peak about 1.0.

    Four slow chords of detuned sine partials with long crossfades, a quiet
    sub-octave root and a slow tremolo. No samples or third-party audio.
    """
    chords = [  # frequencies in Hz: D minor 9, B-flat major 7, F add 9, C sus 2
        (146.83, 220.00, 261.63, 329.63),
        (116.54, 174.61, 220.00, 293.66),
        (174.61, 261.63, 329.63, 392.00),
        (130.81, 196.00, 293.66, 392.00),
    ]
    bar = 8.0
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    out = np.zeros((n, 2))
    rng = np.random.default_rng(7)
    for index in range(int(seconds / bar) + 2):
        start = index * bar - 2.0  # chords overlap by two seconds on each side
        local = t - start
        envelope = np.clip(local / 4.0, 0, 1) * np.clip((bar + 4.0 - local) / 4.0, 0, 1)
        envelope = np.sin(envelope * np.pi / 2) ** 2
        if not envelope.any():
            continue
        notes = chords[index % len(chords)]
        for k, freq in enumerate((notes[0] / 2, *notes)):
            weight = 0.9 if k == 0 else 0.55 / (1 + 0.35 * k)
            for side, detune in enumerate((-0.0016, 0.0019)):
                phase = rng.uniform(0, 2 * np.pi)
                tone = np.sin(2 * np.pi * freq * (1 + detune) * t + phase)
                tone += 0.22 * np.sin(2 * np.pi * 2 * freq * (1 - detune) * t + phase * 1.7)
                out[:, side] += weight * envelope * tone
    out *= (0.86 + 0.14 * np.sin(2 * np.pi * 0.07 * t))[:, None]
    return out / np.max(np.abs(out))


def audio() -> None:
    plan = json.loads((BUILD / "timeline.json").read_text(encoding="utf-8"))
    total = plan["total"]
    n = int(total * RATE)
    voice = np.zeros(n)
    for scene in plan["scenes"]:
        for sentence in scene["sentences"]:
            clip = read_voice(BUILD / "voice" / sentence["file"])
            at = int((scene["offset"] + sentence["start"]) * RATE)
            voice[at : at + len(clip)] += clip[: n - at]
    voice *= 0.89 / np.max(np.abs(voice))

    # Duck the bed under speech: follow the narration level, then smooth so the
    # music moves gently instead of pumping.
    speaking = smooth((smooth(np.abs(voice), 0.05) > 0.01).astype(float), 0.9)
    bed_gain = 0.30 - 0.20 * np.clip(speaking * 1.4, 0, 1)
    fade = np.clip(np.arange(n) / (2.5 * RATE), 0, 1) * np.clip((n - np.arange(n)) / (3.0 * RATE), 0, 1)
    bed = ambient_bed(total)[:n] * (bed_gain * fade)[:, None]

    mix = bed + voice[:, None]
    mix *= 0.89 / np.max(np.abs(mix))  # about -1 dBFS peak, no clipping
    for name, track in (("mix", mix), ("voice", np.repeat(voice[:, None], 2, axis=1)), ("music", bed)):
        with wave.open(str(BUILD / f"{name}.wav"), "wb") as wav:
            wav.setnchannels(2)
            wav.setsampwidth(2)
            wav.setframerate(RATE)
            wav.writeframes((np.clip(track, -1, 1) * 32767).astype(np.int16).tobytes())
    print(f"mix.wav: {total:.2f}s, peak {20 * np.log10(np.max(np.abs(mix))):.1f} dBFS")


# -- assembly ----------------------------------------------------------------


def stamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def run(*args: str) -> None:
    subprocess.check_call(args)  # noqa: S603


def assemble() -> None:
    plan = json.loads((BUILD / "timeline.json").read_text(encoding="utf-8"))
    frames = json.loads((BUILD / "frames.json").read_text(encoding="utf-8"))

    # Each recorded frame is shown for as long as it was on screen. Scenes were
    # recorded against the narration clock, so each one already has its length.
    lines = []
    for scene in plan["scenes"]:
        shots = [f for f in frames if f["scene"] == scene["id"]]
        for shot, following in zip(shots, shots[1:] + [None]):
            end = following["t"] if following else scene["duration"]
            if end - shot["t"] > 0:
                lines += [f"file '{(BUILD / shot['file']).as_posix()}'", f"duration {end - shot['t']:.4f}"]
    lines.append(lines[-2])  # the concat demuxer needs the last file repeated
    (BUILD / "video.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    srt, index = [], 1
    for scene in plan["scenes"]:
        for sentence in scene["sentences"]:
            start, end = scene["offset"] + sentence["start"], scene["offset"] + sentence["end"] + 0.25
            srt.append(f"{index}\n{stamp(start)} --> {stamp(end)}\n{sentence['text']}\n")
            index += 1
    OUTPUT.with_suffix(".srt").write_text("\n".join(srt), encoding="utf-8")

    run("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(BUILD / "video.txt"),
        "-i", str(BUILD / "mix.wav"),
        "-vf", f"fps={FPS},scale=1920:1080:flags=lanczos:in_range=full:out_range=tv,format=yuv420p",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", "18", "-color_range", "tv",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
        "-t", f"{plan['total']:.3f}", str(OUTPUT))
    print(f"{OUTPUT.name}: {OUTPUT.stat().st_size / 1e6:.1f} MB, {len(frames)} source frames")


if __name__ == "__main__":
    commands = {"timeline": timeline, "audio": audio, "assemble": assemble}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        sys.exit(__doc__)
    commands[sys.argv[1]]()
