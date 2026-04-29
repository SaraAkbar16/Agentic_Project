"""Phase 1 schema models for story/script generation.

These models enforce a strict JSON contract so downstream agents can safely
consume machine-readable state without additional normalization.
"""

from __future__ import annotations

import re
from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


CHARACTER_ID_PATTERN = re.compile(r"^char_\d{2}$")
SCENE_ID_PATTERN = re.compile(r"^scene_\d{2}$")
LINE_ID_PATTERN = re.compile(r"^line_\d{2}$")


class VoiceProfile(BaseModel):
    """Voice rendering metadata for downstream TTS usage."""

    model_config = ConfigDict(extra="forbid")

    gender: Literal["male", "female", "neutral"]
    age: Literal["child", "young", "adult", "old"]
    tone: Literal["calm", "energetic", "whisper", "deep"]
    tts_engine: Literal["auto"] = "auto"
    voice_id: str | None = None


class VisualProfile(BaseModel):
    """Text-only visual description used later by image/video stages."""

    model_config = ConfigDict(extra="forbid")

    appearance: str = Field(min_length=1)
    clothing: str = Field(min_length=1)
    style: Literal["fantasy", "cartoon", "realistic"]


class Meta(BaseModel):
    """Versioning and trace metadata for a generated project state."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    user_prompt: str = Field(min_length=1)
    current_version: int = 1
    created_at: str
    last_updated: str
    status: Literal["completed"] = "completed"

    @field_validator("current_version")
    @classmethod
    def validate_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError("current_version must be 1 for Phase 1")
        return value


class Story(BaseModel):
    """High-level story definition inferred from the user prompt."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3)
    genre: str = Field(min_length=2)
    tone: str = Field(min_length=2)
    theme: str = Field(min_length=2)
    summary: str = Field(min_length=20)


class Character(BaseModel):
    """Character definition used by scenes and dialogues."""

    model_config = ConfigDict(extra="forbid")

    character_id: str
    name: str = Field(min_length=1)
    role: Literal["protagonist", "antagonist", "narrator", "side"]
    personality: str = Field(min_length=1)
    voice_profile: VoiceProfile
    visual_profile: VisualProfile

    @field_validator("character_id")
    @classmethod
    def validate_character_id(cls, value: str) -> str:
        if not CHARACTER_ID_PATTERN.match(value):
            raise ValueError("character_id must match char_XX")
        return value


class Dialogue(BaseModel):
    """A single dialogue line spoken by a known character."""

    model_config = ConfigDict(extra="forbid")

    line_id: str
    character_id: str
    text: str = Field(min_length=1)
    emotion: str = Field(min_length=2)

    @field_validator("line_id")
    @classmethod
    def validate_line_id(cls, value: str) -> str:
        if not LINE_ID_PATTERN.match(value):
            raise ValueError("line_id must match line_XX_YY")
        return value

    @field_validator("character_id")
    @classmethod
    def validate_character_id_ref_format(cls, value: str) -> str:
        if not CHARACTER_ID_PATTERN.match(value):
            raise ValueError("dialogue character_id must match char_XX")
        return value


class Scene(BaseModel):
    """A scene with visuals and dialogue lines."""

    model_config = ConfigDict(extra="forbid")

    scene_id: str
    order: int
    title: str = Field(min_length=2)
    visual_description: str = Field(min_length=20)
    mood: str = Field(min_length=2)
    setting: str = Field(min_length=1)
    duration_sec: int = Field(ge=5, le=180)
    dialogues: List[Dialogue] = Field(default_factory=list)

    @field_validator("scene_id")
    @classmethod
    def validate_scene_id(cls, value: str) -> str:
        if not SCENE_ID_PATTERN.match(value):
            raise ValueError("scene_id must match scene_XX")
        return value


class Phase1State(BaseModel):
    """Strict state object produced by the Phase 1 story agent."""

    model_config = ConfigDict(extra="forbid")

    meta: Meta
    story: Story
    characters: List[Character]
    scenes: List[Scene]

    @field_validator("characters")
    @classmethod
    def validate_character_count(cls, value: List[Character]) -> List[Character]:
        if not 1 <= len(value) <= 5:
            raise ValueError("characters must contain between 1 and 5 entries")
        return value

    @field_validator("scenes")
    @classmethod
    def validate_scene_count(cls, value: List[Scene]) -> List[Scene]:
        if not 3 <= len(value) <= 6:
            raise ValueError("scenes must contain between 3 and 6 entries")
        return value

    @model_validator(mode="after")
    def validate_cross_references(self) -> "Phase1State":
        character_ids = {character.character_id for character in self.characters}
        expected_scene_order = list(range(1, len(self.scenes) + 1))
        actual_scene_order = [scene.order for scene in self.scenes]
        expected_line_counter = 1

        if actual_scene_order != expected_scene_order:
            raise ValueError("scene order must be sequential starting from 1")

        for scene in self.scenes:
            for dialogue in scene.dialogues:
                expected_line_id = f"line_{expected_line_counter:02d}"
                if dialogue.line_id != expected_line_id:
                    raise ValueError("dialogue line_id must be sequential starting from line_01")
                if dialogue.character_id not in character_ids:
                    raise ValueError(
                        f"dialogue references unknown character_id: {dialogue.character_id}"
                    )
                expected_line_counter += 1

        return self
