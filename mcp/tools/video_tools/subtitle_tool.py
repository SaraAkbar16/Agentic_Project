"""Tool for generating SRT subtitle files.

This tool converts timing manifest data into a standard .srt subtitle file.
"""

import logging
from pathlib import Path
from typing import Dict, Any


logger = logging.getLogger("phase3.subtitle")


def format_timestamp(ms: int) -> str:
    """Convert milliseconds to SRT timestamp format HH:MM:SS,mmm."""
    seconds = ms // 1000
    milliseconds = ms % 1000
    minutes = seconds // 60
    seconds = seconds % 60
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def generate_srt(timing_manifest: Dict[str, Any], output_path: str) -> str:
    """
    Generate an SRT file from the timing manifest.

    The manifest is expected to have a 'scenes' list, each containing 
    'audio_segments' with 'start_ms', 'end_ms', and 'line'.
    """
    logger.info(f"Generating SRT at {output_path}")
    
    lines = []
    counter = 1
    
    # Track global time offset if manifest uses relative scene times
    # However, Phase 2 timing_manifest usually has absolute project times 
    # or per-scene times. Let's assume per-scene segments but we need to 
    # track the cumulative duration to make a project-wide SRT.
    
    current_offset_ms = 0
    
    for scene in timing_manifest.get("scenes", []):
        scene_duration = scene.get("total_duration_ms", 0)
        
        for segment in scene.get("audio_segments", []):
            start_ms = segment["start_ms"] + current_offset_ms
            end_ms = segment["end_ms"] + current_offset_ms
            text = segment.get("line", "")
            character = segment.get("character", "")
            
            if text:
                display_text = f"{character}: {text}" if character else text
                lines.append(f"{counter}")
                lines.append(f"{format_timestamp(start_ms)} --> {format_timestamp(end_ms)}")
                lines.append(display_text)
                lines.append("")
                counter += 1
        
        current_offset_ms += scene_duration

    # Ensure parent directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    logger.info(f"SRT generated with {counter-1} entries")
    return output_path
