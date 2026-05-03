"""Phase 3: Video Generation Agent.

This agent orchestrates the production of the final video by coordinating 
image generation via ComfyUI and video composition via FFmpeg.
"""

import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv

from shared.schemas.phase3_schema import (
    Phase3State, Phase3Output, Phase3Summary, 
    SceneClipOutput
)
from mcp.tools.vision_tools import image_gen_tool
from mcp.tools.video_tools import compositor_tool, subtitle_tool, wav2lip_tool, ffmpeg_tool


# Load environment variables
load_dotenv()

# Constants
BASE_DIR = Path(__file__).parent.parent.parent
DEFAULT_DATA_DIR = BASE_DIR / "data/outputs"
DEFAULT_RESOLUTION = "1280x720"
DEFAULT_FPS = 24

logger = logging.getLogger("phase3.video_agent")


class VideoAgent:
    """Agent responsible for Phase 3 orchestration."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the VideoAgent with configuration.
        """
        self.config = config or {}
        self.comfy_url = self.config.get("comfy_url") or os.getenv("COMFY_URL", "http://127.0.0.1:8188")
        self.fps = self.config.get("fps", DEFAULT_FPS)
        self.resolution = self.config.get("resolution", DEFAULT_RESOLUTION)
        self.subtitles = self.config.get("subtitles", False)
        self.force = self.config.get("force", False)
        
        self.phase1_state_file = self.config.get("phase1_state_file")
        self.timing_manifest_file = self.config.get("timing_manifest_file")

        # 1. Identity
        self.project_id = self.config.get("project_id")
        if not self.project_id:
            # Try to derive from phase1_state_file name
            if self.phase1_state_file:
                name = Path(self.phase1_state_file).stem
                if "phase1_state_" in name:
                    self.project_id = name.replace("phase1_state_", "project_")
                elif "phase2_state_" in name:
                    self.project_id = name.replace("phase2_state_", "project_")
                else:
                    # Generic project ID from filename
                    self.project_id = f"project_{name}"
            
        if not self.project_id:
            self.project_id = "project_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 2. Paths
        self.data_dir = Path(self.config.get("data_dir", DEFAULT_DATA_DIR))
        
        # 3. Project Output Directory (Isolated)
        self.project_dir = self.data_dir / "video/phase3" / self.project_id
        self.frames_dir = self.data_dir / "video/phase3/frames"
        self.clips_dir = self.project_dir / "clips"
        
        # Memory for continuous music
        self.bgm_playtime = {}
        
        # Ensure directories exist
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.clips_dir.mkdir(parents=True, exist_ok=True)

    def _load_phase1_state(self) -> Dict[str, Any]:
        if not self.phase1_state_file:
            self.phase1_state_file = self._find_latest_phase1_state()
        with open(self.phase1_state_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_timing_manifest(self) -> List[Dict[str, Any]]:
        if not self.timing_manifest_file:
            self.timing_manifest_file = self.data_dir / "timing_manifest.json"
        with open(self.timing_manifest_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _find_latest_phase1_state(self) -> Path:
        files = list(self.data_dir.glob("phase1_state_*.json"))
        if not files:
            raise FileNotFoundError(f"No Phase 1 state files found in {self.data_dir}")
        return sorted(files, key=lambda x: x.name, reverse=True)[0]

    def _get_timing_manifest_scene(self, scene_id: str, timing_manifest: List[Dict[str, Any]], scene_data: Dict[str, Any]) -> Dict[str, Any]:
        scene_segments = [s for s in timing_manifest if s.get("scene_id") == scene_id]
        if not scene_segments:
            return {"scene_id": scene_id, "total_duration_ms": 5000, "audio_segments": [], "bgm_file": None}
        
        scene_start_ms = min(s.get("start_ms", 0) for s in scene_segments)
        scene_end_ms = max(s.get("end_ms", 0) for s in scene_segments)
        duration_ms = scene_end_ms - scene_start_ms
        
        # Match segments with dialogue text from scene_data
        dialogues = scene_data.get("dialogues", [])
        audio_segments = []
        bgm_file = None
        
        for i, s in enumerate(scene_segments):
            text = dialogues[i].get("text", "") if i < len(dialogues) else ""
            # Extract BGM if present in the manifest
            if not bgm_file and s.get("bgm_file"):
                bgm_file = s["bgm_file"]
                
            audio_segments.append({
                "character": s.get("character_id", ""),
                "line": text, 
                "audio_file": str(self.data_dir / s["audio_file"]),
                "start_ms": s["start_ms"] - scene_start_ms,
                "end_ms": s["end_ms"] - scene_start_ms
            })
            
        return {
            "scene_id": scene_id,
            "total_duration_ms": duration_ms,
            "audio_segments": audio_segments,
            "bgm_file": str(BASE_DIR / bgm_file) if bgm_file else None
        }

    def _save_state(self, state: Phase3State):
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        state_file = self.data_dir / f"phase3_state_{timestamp_str}.json"
        with open(state_file, "w", encoding="utf-8") as f:
            f.write(state.model_dump_json(indent=2))

    def run(self) -> Phase3State:
        """Execute the Video Generation & Composition pipeline."""
        logger.info("\n" + "="*50 + "\nPHASE 3: VIDEO GENERATION PIPELINE STARTING\n" + "="*50)
        logger.info(f"Project ID: {self.project_id}")
        logger.info(f"Project Dir: {self.project_dir}")
        
        # 1. Setup
        phase1_state = self._load_phase1_state()
        timing_manifest = self._load_timing_manifest()
        scenes_data = phase1_state.get("scenes", [])
        
        processed_scenes = []
        total_duration_sec = 0.0
        
        for i, scene in enumerate(scenes_data, 1):
            scene_id = scene["scene_id"]
            scene_title = scene.get("title", scene_id)
            logger.info(f"\n[Scene {i}/{len(scenes_data)}] {scene_title}")
            
            try:
                frame_path, full_prompt = self._ensure_frame(scene, self.project_id, phase1_state)
                clip_path, duration_sec = self._ensure_clip(scene, frame_path, timing_manifest, phase1_state)
                
                total_duration_sec += duration_sec
                processed_scenes.append(SceneClipOutput(
                    scene_id=scene_id,
                    clip_path=clip_path,
                    duration_seconds=duration_sec,
                    frame_path=frame_path,
                    animation_effect=compositor_tool.get_animation_effect(scene),
                    image_prompt_used=full_prompt,
                    comfy_workflow_used="wan2.1_t2i"
                ))
            except Exception as e:
                logger.error(f"  !! Failed scene {scene_id}: {e}")
                continue

        logger.info("\n[Final Assembly] Concatenating all scenes...")
        final_video_path = str(self.project_dir / "final_output.mp4")
        clip_paths = [s.clip_path for s in processed_scenes]
        transitions = ["cut"] * (len(clip_paths) - 1)
        
        try:
            compositor_tool.compose_final_video(clip_paths, transitions, final_video_path)
            
            if self.subtitles:
                logger.info("[Final Assembly] Burning subtitles...")
                tm_for_srt = {"scenes": [self._get_timing_manifest_scene(s["scene_id"], timing_manifest, s) for s in scenes_data]}
                srt_path = str(self.project_dir / "subtitles.srt")
                subtitle_tool.generate_srt(tm_for_srt, srt_path)
                subtitled_video_path = str(self.project_dir / "final_output_subtitled.mp4")
                final_video_path = ffmpeg_tool.burn_subtitles(final_video_path, srt_path, subtitled_video_path)
            
            logger.info(f"\n" + "="*50 + f"\nPIPELINE COMPLETE: {final_video_path}\n" + "="*50)
            
            state = Phase3State(
                phase=3,
                status="completed",
                timestamp=datetime.now().isoformat(),
                inputs={"phase1_state_file": str(self.phase1_state_file), "timing_manifest_file": str(self.timing_manifest_file)},
                outputs=Phase3Output(frames_dir=str(self.frames_dir), clips_dir=str(self.clips_dir), final_video=final_video_path),
                scenes=processed_scenes,
                errors=[],
                summary=Phase3Summary(total_scenes=len(processed_scenes), total_duration_seconds=total_duration_sec, resolution=self.resolution, fps=self.fps)
            )
            self._save_state(state)
            return state
        except Exception as e:
            logger.error(f"\n[CRITICAL] Final composition failed: {e}")
            raise RuntimeError(f"Final composition error: {e}")

    def _ensure_frame(self, scene: Dict[str, Any], project_id: str, phase1_state: Dict[str, Any]) -> tuple:
        """Ensure a frame exists for the scene, either from cache or generation."""
        scene_id = scene["scene_id"]
        cached_path = self.frames_dir / f"scene_{project_id}_{scene_id}.png"
        
        visual_desc = scene.get("visual_description", "")
        visual_prompt = scene.get("visual_prompt", "") 
        
        # 1. Identify characters in this scene
        char_ids_in_scene = {d.get("character_id") for d in scene.get("dialogues", [])}
        # Also check if character name is in visual description
        all_chars = phase1_state.get("characters", [])
        char_descs = []
        focused_char_name = None
        
        for char in all_chars:
            name = char.get("name", "").lower()
            if char.get("character_id") in char_ids_in_scene or (name and name in visual_desc.lower()):
                char_descs.append(char.get("visual_description", ""))
                if not focused_char_name:
                    focused_char_name = char.get("name")

        # 2. Construct Forced Character Prompt
        # We put the character description AT THE FRONT to give it the most weight in ComfyUI
        if char_descs:
            # Force character rendering with anchoring keywords
            anchor = "Cinematic portrait of" if ("close-up" in visual_desc.lower() or "face" in visual_desc.lower()) else "Full body shot of"
            main_subject = ". ".join(char_descs)
            full_prompt = f"{anchor} {main_subject}, {visual_desc}, {visual_prompt}, highly detailed character features, cinematic lighting, 8k"
            logger.info(f"  -> [Prompt] Character focused: {focused_char_name or 'Unknown'}")
        else:
            full_prompt = f"{visual_desc}, {visual_prompt}, cinematic lighting, 8k"

        if cached_path.exists() and not self.force:
            logger.info(f"  -> [1/3] Frame: Using cached frame.")
            return str(cached_path), full_prompt
        
        logger.info(f"  -> [1/3] Frame: Generating via ComfyUI...")
        frame_path = image_gen_tool.generate_image(
            prompt=full_prompt,
            scene_id=f"{project_id}_{scene_id}",
            comfy_url=self.comfy_url
        )
        return frame_path, full_prompt

    def _ensure_clip(self, scene: Dict[str, Any], frame_path: str, timing_manifest: List[Dict[str, Any]], phase1_state: Dict[str, Any]) -> tuple:
        scene_id = scene["scene_id"]
        final_clip_path = self.clips_dir / f"{scene_id}.mp4"
        
        tm_scene = self._get_timing_manifest_scene(scene_id, timing_manifest, scene)
        duration_sec = tm_scene["total_duration_ms"] / 1000.0
        bgm_file = tm_scene.get("bgm_file")
        
        # Calculate offset for continuous music
        bgm_offset_ms = 0
        if bgm_file:
            bgm_offset_ms = self.bgm_playtime.get(bgm_file, 0)

        # Caching check
        if final_clip_path.exists() and not self.force:
            logger.info(f"  -> [2/3] Clip: Using cached clip.")
            if bgm_file:
                self.bgm_playtime[bgm_file] = bgm_offset_ms + tm_scene["total_duration_ms"]
            return str(final_clip_path), duration_sec

        dialogue_exists = len(scene.get("dialogues", [])) > 0
        visual_text = (scene.get("visual_description", "") + scene.get("visual_prompt", "")).lower()
        char_names = [c.get("name", "").lower() for c in phase1_state.get("characters", []) if c.get("name")]
        
        has_face_kw = any(kw in visual_text for kw in ["close-up", "close up", "face", "portrait", "talking", "speaking"])
        mentions_char = any(name in visual_text for name in char_names)
        
        if dialogue_exists and (has_face_kw or mentions_char):
            try:
                char_id = scene.get("dialogues", [])[0].get("character_id", "Char")
                char_name = next((c.get("name", char_id) for c in phase1_state.get("characters", []) if c["character_id"] == char_id), char_id)
                logger.info(f"  -> [2/3] Character: {char_name} detected.")
                
                # Composition with BGM offset
                base_clip = compositor_tool.compose_scene(
                    scene=scene, 
                    frame_path=frame_path, 
                    timing_manifest_scene=tm_scene, 
                    clips_dir=str(self.clips_dir), 
                    fps=self.fps, 
                    resolution=self.resolution,
                    bgm_offset_ms=bgm_offset_ms
                )
                temp_audio = str(self.clips_dir / f"temp_{scene_id}.wav")
                # ... rest of wav2lip logic remains similar
                from mcp.tools.video_tools.ffmpeg_tool import FFMPEG_EXE
                subprocess.run([FFMPEG_EXE, "-y", "-i", base_clip, "-vn", "-acodec", "pcm_s16le", temp_audio], check=True, capture_output=True)
                
                logger.info(f"  -> [3/3] Syncing: Running Wav2Lip...")
                synced_path = str(self.clips_dir / f"synced_{scene_id}.mp4")
                final_video = wav2lip_tool.sync_lips(frame_path, temp_audio, synced_path)
                
                # Update playtime memory
                if bgm_file:
                    self.bgm_playtime[bgm_file] = bgm_offset_ms + tm_scene["total_duration_ms"]
                    
                return final_video, duration_sec
            except Exception as e:
                logger.warning(f"  -> [Phase 3] Lip Sync skipped for {scene_id}: {e}")

        # Fallback to standard Ken Burns clip
        logger.info(f"  -> [3/3] Animation: Composing Ken Burns clip...")
        clip_path = compositor_tool.compose_scene(
            scene=scene, 
            frame_path=frame_path, 
            timing_manifest_scene=tm_scene, 
            clips_dir=str(self.clips_dir), 
            fps=self.fps, 
            resolution=self.resolution,
            bgm_offset_ms=bgm_offset_ms
        )
        
        # Update playtime memory
        if bgm_file:
            self.bgm_playtime[bgm_file] = bgm_offset_ms + tm_scene["total_duration_ms"]
            
        final_clip_path = self.clips_dir / f"{self.project_id}_{scene_id}.mp4"
        ffmpeg_tool.normalize_video(clip_path, str(final_clip_path), self.fps, self.resolution)
        return str(final_clip_path), duration_sec
