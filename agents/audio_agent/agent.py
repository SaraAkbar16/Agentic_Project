"""Phase 2: Audio generation agent.

This module provides a simple, deterministic audio generation implementation
that follows the Phase-2 requirements. It prefers system TTS if available
(`pyttsx3`) and otherwise generates silent WAV files whose duration is a
deterministic function of the dialogue text length. The module does not
call external APIs or log secrets.
"""

from __future__ import annotations

import json
import logging
import os
import wave
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _duration_ms_from_text(text: str) -> int:
    """Deterministic duration estimator (ms) based on text length.

    Keeps results reasonable and deterministic so timing metadata is stable.
    """
    words = len(str(text or "").split())
    # base 600ms + 300ms per word, capped at 120s per line
    ms = 600 + words * 300
    return min(ms, 120_000)


def _write_silent_wav(path: str, duration_ms: int, sample_rate: int = 22050) -> None:
    """Write a silent WAV file of approximately duration_ms."""
    n_frames = int(sample_rate * (duration_ms / 1000.0))
    n_channels = 1
    sampwidth = 2

    with wave.open(path, "wb") as wf:
        wf.setnchannels(n_channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        # write silence
        wf.writeframes(b"\x00" * n_frames * sampwidth)


def _try_tts_save(text: str, path: str) -> int:
    """Attempt to use pyttsx3 to save speech to `path`.

    Returns the duration in ms based on the produced file. If pyttsx3 isn't
    available or an error occurs, returns 0.
    """
    try:
        import pyttsx3

        engine = pyttsx3.init()
        # ensure folder exists before saving
        dirname = os.path.dirname(path)
        _ensure_dir(dirname)
        engine.save_to_file(text or "", path)
        engine.runAndWait()

        # measure duration from WAV file if produced
        try:
            with wave.open(path, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration_s = frames / float(rate)
                return int(duration_s * 1000)
        except Exception:
            return 0
    except Exception:
        return 0


def _generate_dialogue_audio_lines(
    phase1: Dict[str, Any],
    output_dir: str,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Generate audio files for each dialogue line and return dialogue_tracks.

    Returns (dialogue_tracks, generated_files)
    """
    characters = {c["character_id"] for c in phase1.get("characters", [])}
    if not characters:
        raise ValueError("Phase-1 JSON must contain at least one character")

    # gather dialogues in scene order
    scenes = sorted(phase1.get("scenes", []), key=lambda s: s.get("order", 0))
    # validate and flatten dialogues
    flat_dialogues: List[Dict[str, Any]] = []
    for scene in scenes:
        for dlg in scene.get("dialogues", []):
            if "line_id" not in dlg:
                raise ValueError("Every dialogue must have a line_id")
            if "character_id" not in dlg:
                raise ValueError("Every dialogue must have a character_id")
            if dlg["character_id"] not in characters:
                raise ValueError(f"Unknown character_id referenced: {dlg['character_id']}")
            # Add scene_id to dialogue for tracking
            dlg["scene_id"] = scene.get("scene_id", "unknown_scene")
            flat_dialogues.append(dlg)

    dialogue_dir = os.path.join(output_dir, "audio", "phase2", "dialogue")
    _ensure_dir(dialogue_dir)

    dialogue_tracks: List[Dict[str, Any]] = []
    generated_files: List[str] = []
    start_ms = 0

    for dlg in flat_dialogues:
        line_id = dlg["line_id"]
        character_id = dlg["character_id"]
        text = dlg.get("text", "")

        filename = f"{line_id}.wav"
        filepath = os.path.join(dialogue_dir, filename)
        relpath = os.path.join("audio", "phase2", "dialogue", filename).replace("\\", "/")

        # try TTS first; if not available, write silent WAV with deterministic length
        duration_ms = _try_tts_save(text, filepath)
        if duration_ms == 0:
            print(f" [AudioAgent] TTS failed for line {line_id}, falling back to silent WAV.")
            duration_ms = _duration_ms_from_text(text)
            _write_silent_wav(filepath, duration_ms)
        else:
            print(f"[AudioAgent] Generated audio for line {line_id} ({duration_ms}ms)")

        end_ms = start_ms + duration_ms

        dialogue_tracks.append(
            {
                "line_id": line_id,
                "scene_id": dlg["scene_id"],
                "character_id": character_id,
                "audio_file": relpath,
                "start_ms": int(start_ms),
                "end_ms": int(end_ms),
            }
        )
        generated_files.append(filepath)
        start_ms = end_ms

    return dialogue_tracks, generated_files


def run_phase2_on_file(phase1_path: str) -> Dict[str, Any]:
    """Process a Phase-1 JSON file and emit Phase-2 augmented JSON.

    This function strictly operates only on the provided file and writes all
    outputs into the same directory as the input file.
    """
    phase1_path = os.path.abspath(phase1_path)
    parent = os.path.dirname(phase1_path)

    with open(phase1_path, "r", encoding="utf-8") as fh:
        phase1 = json.load(fh)

    # generate dialogue audio and timings
    dialogue_tracks, generated_files = _generate_dialogue_audio_lines(phase1, parent)

    # build audio block
    audio_block = {"dialogue_tracks": dialogue_tracks, "background_music": []}

    # prepare phase2 state copy
    phase2 = dict(phase1)  # shallow copy top-level
    phase2["audio"] = audio_block

    # update meta
    meta = dict(phase2.get("meta", {}))
    meta["current_version"] = 2
    meta["last_updated"] = _iso_now()
    phase2["meta"] = meta

    # versions list
    versions = phase2.get("versions") or []
    versions.append(
        {
            "version": 2,
            "change_summary": "Generated dialogue audio",
            "changed_by": "phase_2_audio_agent",
        }
    )
    phase2["versions"] = versions

    # Save timing manifest separately as required
    timing_manifest = []
    for track in dialogue_tracks:
        timing_manifest.append({
            "scene_id": track["scene_id"],
            "audio_file": track["audio_file"],
            "start_ms": track["start_ms"],
            "end_ms": track["end_ms"]
        })
    
    manifest_path = os.path.join(parent, "timing_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(timing_manifest, fh, indent=2, ensure_ascii=False)
    print(f"[AudioAgent] Timing manifest saved to: {manifest_path}")

    return phase2


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m agents.audio_agent.agent <phase1_json_path>")
        raise SystemExit(2)

    out = run_phase2_on_file(sys.argv[1])
    print("Generated Phase-2 state (in-memory).")
