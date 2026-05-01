"""Tool for orchestrating video composition.

This tool coordinates the animation of frames and the merging of audio
to produce scene clips, and finally concatenates those clips into a full video.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

from mcp.tools.video_tools import ffmpeg_tool


logger = logging.getLogger("phase3.compositor")


def get_animation_effect(tone: str) -> str:
    """Map scene tone to a Ken Burns animation effect."""
    tone = tone.lower()
    if any(t in tone for t in ["action", "tense", "exciting"]):
        return "zoom_in"
    if any(t in tone for t in ["melancholic", "reflective", "sad", "calm"]):
        return "pan_left"
    if any(t in tone for t in ["hopeful", "uplifting", "happy"]):
        return "zoom_out"
    return "static"


def compose_scene(
    scene: Dict[str, Any],
    frame_path: str,
    timing_manifest_scene: Dict[str, Any],
    clips_dir: str,
    fps: int = 24,
    resolution: str = "1280x720"
) -> str:
    """
    Produce a complete video clip for a single scene.
    
    Steps:
    1. Determine effect.
    2. Apply Ken Burns.
    3. Merge audio (dialogue + BGM).
    """
    scene_id = scene["scene_id"]
    tone = scene.get("mood") or scene.get("tone") or "default"
    effect = get_animation_effect(tone)
    duration_ms = timing_manifest_scene["total_duration_ms"]
    duration_sec = duration_ms / 1000.0
    
    clips_dir_path = Path(clips_dir)
    clips_dir_path.mkdir(parents=True, exist_ok=True)
    
    silent_clip_path = str(clips_dir_path / f"silent_{scene_id}.mp4")
    final_clip_path = str(clips_dir_path / f"{scene_id}.mp4")
    
    logger.info(f"Composing scene {scene_id} with effect: {effect}")
    
    # Step 1: Animation
    ffmpeg_tool.apply_ken_burns(
        input_image=frame_path,
        output_video=silent_clip_path,
        duration_seconds=duration_sec,
        effect=effect,
        fps=fps,
        resolution=resolution
    )
    
    # Step 2: Audio Merge
    audio_segments = timing_manifest_scene.get("audio_segments", [])
    bgm_path = timing_manifest_scene.get("bgm_file")
    
    ffmpeg_tool.merge_audio_to_clip(
        video_path=silent_clip_path,
        audio_segments=audio_segments,
        bgm_path=bgm_path,
        output_path=final_clip_path,
        total_duration_ms=duration_ms
    )
    
    # Cleanup temporary silent clip
    try:
        Path(silent_clip_path).unlink()
    except Exception as e:
        logger.warning(f"Failed to delete temporary file {silent_clip_path}: {e}")
        
    return final_clip_path


def compose_final_video(
    scene_clip_paths: List[str],
    transitions: List[str],
    output_path: str
) -> str:
    """
    Concatenate all scene clips into the final movie.
    """
    logger.info(f"Concatenating {len(scene_clip_paths)} clips into {output_path}")
    return ffmpeg_tool.concatenate_clips(
        clip_paths=scene_clip_paths,
        transitions=transitions,
        output_path=output_path
    )
