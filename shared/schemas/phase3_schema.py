"""Phase 3 schema models for video generation and composition.

These models define the structure of the data produced during the video
generation phase, including frame paths, clip paths, and final output state.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class SceneFrameOutput(BaseModel):
    """Output metadata for a single generated scene frame."""

    model_config = ConfigDict(extra="forbid")

    scene_id: str = Field(description="ID of the scene this frame belongs to")
    frame_path: str = Field(description="Path to the generated image file")
    image_prompt_used: str = Field(description="The full prompt used for generation")
    animation_effect: str = Field(description="Animation effect assigned to this scene")
    comfy_workflow_used: str = Field(default="wan2.1_t2i")


class SceneClipOutput(BaseModel):
    """Output metadata for a single animated scene clip."""

    model_config = ConfigDict(extra="forbid")

    scene_id: str = Field(description="ID of the scene this clip belongs to")
    clip_path: str = Field(description="Path to the generated MP4 clip")
    duration_seconds: float = Field(description="Duration of the clip in seconds")
    frame_path: str = Field(description="Reference to the source frame path")
    animation_effect: str
    image_prompt_used: str
    comfy_workflow_used: str


class Phase3Output(BaseModel):
    """Container for all Phase 3 file outputs."""

    model_config = ConfigDict(extra="forbid")

    frames_dir: str
    clips_dir: str
    final_video: str


class Phase3Summary(BaseModel):
    """Summary statistics for Phase 3 output."""

    model_config = ConfigDict(extra="forbid")

    total_scenes: int
    total_duration_seconds: float
    resolution: str
    fps: int


class Phase3State(BaseModel):
    """Complete state object for Phase 3."""

    model_config = ConfigDict(extra="forbid")

    phase: int = 3
    status: str = "completed"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    inputs: Dict[str, str] = Field(
        description="Paths to phase1_state_file and timing_manifest_file"
    )
    outputs: Phase3Output
    scenes: List[SceneClipOutput]
    errors: List[str] = Field(default_factory=list)
    summary: Phase3Summary
