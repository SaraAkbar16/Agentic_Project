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


def _get_project_id(phase1: Dict[str, Any]) -> str:
    """Extract project_id from meta or generate one."""
    return phase1.get("meta", {}).get("project_id", "project_" + datetime.now().strftime("%Y%m%d_%H%M%S"))


def _try_tts_save(text: str, path: str, gender: str = "male") -> int:
    """Attempt to use pyttsx3 to save speech to `path` with gender-appropriate voice."""
    try:
        import pyttsx3

        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        
        # Simple gender mapping
        # 0 is usually male, 1 is usually female in default Windows/SAPI5
        if gender == "female" and len(voices) > 1:
            engine.setProperty("voice", voices[1].id)
        else:
            engine.setProperty("voice", voices[0].id)

        # ensure folder exists before saving
        dirname = os.path.dirname(path)
        _ensure_dir(dirname)
        engine.save_to_file(text or "", path)
        engine.runAndWait()

        # measure duration
        try:
            with wave.open(path, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                return int((frames / float(rate)) * 1000)
        except Exception:
            return 0
    except Exception:
        return 0


def _generate_dialogue_audio_lines(
    phase1: Dict[str, Any],
    output_dir: str,
    project_id: str,
    force: bool = False
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Generate audio files for each dialogue line in project-specific folders."""
    
    # Map character IDs to genders based on structured voice_profile
    char_metadata = {}
    female_keywords = ["female", "woman", "girl", "lady", "queen", "princess", "she", "her", "hers", "mrs", "ms", "miss"]
    
    for c in phase1.get("characters", []):
        char_id = c.get("character_id")
        
        # 1. Try structured voice_profile gender first
        gender = c.get("voice_profile", {}).get("gender")
        
        # 2. Fallback to keyword scanning
        if not gender:
            name = c.get("name", "").lower()
            v_desc = c.get("visual_profile", {}).get("appearance", "").lower() # Note: structured visual_profile
            desc = c.get("personality", "").lower()
            
            full_text = f"{name} {v_desc} {desc}"
            gender = "female" if any(kw in full_text for kw in female_keywords) else "male"
        else:
            gender = gender.lower()
            
        char_metadata[char_id] = {"gender": gender, "name": c.get("name", char_id)}
        print(f" [AudioAgent] Character '{char_metadata[char_id]['name']}' ({char_id}) detected as: {gender.upper()}")

    # Gather dialogues in scene order
    scenes = sorted(phase1.get("scenes", []), key=lambda s: s.get("order", 0))
    flat_dialogues: List[Dict[str, Any]] = []
    for scene in scenes:
        for dlg in scene.get("dialogues", []):
            dlg["scene_id"] = scene.get("scene_id", "unknown_scene")
            flat_dialogues.append(dlg)

    # Isolated project directory
    dialogue_dir = os.path.join(output_dir, "audio", "phase2", project_id, "dialogue")
    _ensure_dir(dialogue_dir)

    dialogue_tracks: List[Dict[str, Any]] = []
    generated_files: List[str] = []
    start_ms = 0

    for dlg in flat_dialogues:
        line_id = dlg["line_id"]
        char_id = dlg["character_id"]
        text = dlg.get("text", "")
        gender = char_metadata.get(char_id, {}).get("gender", "male")

        filename = f"{line_id}.wav"
        filepath = os.path.join(dialogue_dir, filename)
        # Relative path for the manifest
        relpath = os.path.join("audio", "phase2", project_id, "dialogue", filename).replace("\\", "/")

        # Check if already exists (Simple cache)
        if os.path.exists(filepath) and not force:
            try:
                with wave.open(filepath, "rb") as wf:
                    duration_ms = int((wf.getnframes() / float(wf.getframerate())) * 1000)
                    print(f" [AudioAgent] Using cached {gender} audio for {line_id}")
            except:
                duration_ms = 0
        else:
            if force and os.path.exists(filepath):
                print(f" [AudioAgent] Forcing re-generation for {line_id}...")
            duration_ms = _try_tts_save(text, filepath, gender=gender)

        if duration_ms == 0:
            duration_ms = _duration_ms_from_text(text)
            _write_silent_wav(filepath, duration_ms)
        else:
            print(f"[AudioAgent] Generated {gender} audio for {line_id} ({duration_ms}ms)")

        end_ms = start_ms + duration_ms
        dialogue_tracks.append({
            "line_id": line_id,
            "scene_id": dlg["scene_id"],
            "character_id": char_id,
            "audio_file": relpath,
            "start_ms": int(start_ms),
            "end_ms": int(end_ms),
        })
        generated_files.append(filepath)
        start_ms = end_ms

    return dialogue_tracks, generated_files


def _get_bgm_for_mood(mood: str, assets_dir: str) -> str | None:
    """Find a matching music track in assets/music/ based on the scene mood."""
    music_dir = os.path.join(assets_dir, "assets", "music")
    if not os.path.exists(music_dir):
        return None
        
    mood = mood.lower()
    # Priority mapping
    mapping = {
        "action": ["action", "tense", "fast", "exciting"],
        "reflective": ["reflective", "sad", "calm", "mysterious"],
        "happy": ["happy", "uplifting", "hopeful"],
        "horror": ["horror", "scary", "dark"],
    }
    
    # Try to find a file that matches the mood or a related keyword
    available_files = os.listdir(music_dir)
    if not available_files:
        return None
        
    # 1. Exact match
    for f in available_files:
        if mood in f.lower():
            return os.path.join("assets", "music", f).replace("\\", "/")
            
    # 2. Keyword match
    for category, keywords in mapping.items():
        if any(kw in mood for kw in keywords):
            for f in available_files:
                if category in f.lower():
                    return os.path.join("assets", "music", f).replace("\\", "/")
                    
    # 3. Default to first available if it's the only one, or return None
    return os.path.join("assets", "music", available_files[0]).replace("\\", "/")


def run_phase2_on_file(phase1_path: str, force: bool = False) -> Dict[str, Any]:
    """Process a Phase-1 JSON file and emit Phase-2 augmented JSON."""
    phase1_path = os.path.abspath(phase1_path)
    parent = os.path.dirname(phase1_path)
    # The root of the project is one level up from parent (if parent is data/outputs)
    # Actually, let's use the current CWD or find it.
    root_dir = os.getcwd()

    with open(phase1_path, "r", encoding="utf-8") as fh:
        phase1 = json.load(fh)

    # 1. Identity
    project_id = _get_project_id(phase1)
    
    # 2. Generate dialogue audio
    dialogue_tracks, generated_files = _generate_dialogue_audio_lines(phase1, parent, project_id, force=force)

    # 3. Build timing manifest with BGM
    timing_manifest = []
    scenes = sorted(phase1.get("scenes", []), key=lambda s: s.get("order", 0))
    
    for scene in scenes:
        scene_id = scene["scene_id"]
        scene_tracks = [t for t in dialogue_tracks if t["scene_id"] == scene_id]
        
        # Get BGM for this scene
        bgm_file = _get_bgm_for_mood(scene.get("mood", "default"), root_dir)
        
        for track in scene_tracks:
            timing_manifest.append({
                "scene_id": scene_id,
                "audio_file": track["audio_file"],
                "start_ms": track["start_ms"],
                "end_ms": track["end_ms"],
                "bgm_file": bgm_file # Include BGM path at the track level for Phase 3 to read
            })
    
    # Save manifest
    manifest_path = os.path.join(parent, "audio", "phase2", project_id, "timing_manifest.json")
    _ensure_dir(os.path.dirname(manifest_path))
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(timing_manifest, fh, indent=2, ensure_ascii=False)
    
    main_manifest_path = os.path.join(parent, "timing_manifest.json")
    with open(main_manifest_path, "w", encoding="utf-8") as fh:
        json.dump(timing_manifest, fh, indent=2, ensure_ascii=False)
        
    # prepare phase2 state copy
    phase2 = dict(phase1)
    phase2["audio"] = {"dialogue_tracks": dialogue_tracks, "background_music": []}
    meta = dict(phase2.get("meta", {}))
    meta["project_id"] = project_id
    meta["current_version"] = 2
    meta["last_updated"] = _iso_now()
    phase2["meta"] = meta

    print(f"[AudioAgent] Timing manifest (with BGM) saved to: {manifest_path}")
    return phase2


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m agents.audio_agent.agent <phase1_json_path>")
        raise SystemExit(2)

    out = run_phase2_on_file(sys.argv[1])
    print("Generated Phase-2 state (in-memory).")
