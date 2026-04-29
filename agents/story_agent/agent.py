"""Phase 1 story generation agent.

This module generates strictly validated Phase 1 state JSON from a user prompt.
It is designed as pure logic with no file I/O so it can be called directly from
future LangGraph nodes.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import ValidationError
from dotenv import load_dotenv

from shared.schemas.phase1_schema import Phase1State

logger = logging.getLogger(__name__)

# Load local environment variables early; deployed environments can still inject
# variables through the process manager without relying on .env files.
load_dotenv()


def _normalize_enum_like(
    value: Any,
    allowed: set[str],
    default: str,
    aliases: Dict[str, str] | None = None,
) -> str:
    """Normalize loose LLM enum output into strict schema literals."""

    aliases = aliases or {}
    text = str(value or "").strip().lower()
    if not text:
        return default

    if text in aliases:
        text = aliases[text]

    if text in allowed:
        return text

    return default


class Phase1GenerationError(RuntimeError):
    """Raised when the story agent cannot produce valid Phase 1 state."""


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_llm():
    """Create an LLM client by provider priority based on environment variables."""

    groq_key = os.getenv("GROQ_API_KEY")

    if groq_key:
        try:
            from langchain_groq import ChatGroq
        except ImportError as exc:
            raise Phase1GenerationError(
                "GROQ_API_KEY is set but langchain-groq is not installed."
            ) from exc

        return ChatGroq(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            temperature=0.3,
            max_retries=1,
            timeout=90,
        ), "groq"

    try:
        from langchain_ollama import ChatOllama
    except ImportError as exc:
        raise Phase1GenerationError(
            "No GROQ_API_KEY found and langchain-ollama is not installed for local fallback."
        ) from exc

    return ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0.3,
    ), "ollama"


def _extract_json_text(raw_text: str) -> str:
    """Extract JSON from plain text or fenced markdown output."""

    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        for part in parts:
            candidate = part.strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("{") and candidate.endswith("}"):
                return candidate
    return cleaned


def _normalize_phase1_shape(raw: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    """Normalize likely model drift and enforce deterministic IDs.

    This keeps the output machine-consumable even when an LLM introduces minor
    key drift, while still applying strict schema validation afterwards.
    """

    characters_in: List[Dict[str, Any]] = list(raw.get("characters") or [])
    scenes_in: List[Dict[str, Any]] = list(raw.get("scenes") or [])

    if not isinstance(raw.get("story"), dict):
        raise ValueError("story must be an object")

    characters_out: List[Dict[str, Any]] = []
    character_alias_to_id: Dict[str, str] = {}

    for idx, character in enumerate(characters_in, start=1):
        if not isinstance(character, dict):
            raise ValueError("each character must be an object")

        character_id = f"char_{idx:02d}"
        name = str(character.get("name", "")).strip()
        role = str(character.get("role", "side")).strip().lower() or "side"
        if role not in {"protagonist", "antagonist", "narrator", "side"}:
            role = "side"

        personality = str(character.get("personality", "brave and determined")).strip() or "brave and determined"

        voice_profile = character.get("voice_profile") or {}
        if not isinstance(voice_profile, dict):
            voice_profile = {}
        voice_profile_normalized = {
            "gender": _normalize_enum_like(
                voice_profile.get("gender", "neutral"),
                allowed={"male", "female", "neutral"},
                default="neutral",
                aliases={
                    "man": "male",
                    "boy": "male",
                    "woman": "female",
                    "girl": "female",
                    "nonbinary": "neutral",
                    "non-binary": "neutral",
                    "none": "neutral",
                    "null": "neutral",
                    "unknown": "neutral",
                },
            ),
            "age": _normalize_enum_like(
                voice_profile.get("age", "adult"),
                allowed={"child", "young", "adult", "old"},
                default="adult",
                aliases={
                    "kid": "child",
                    "teen": "young",
                    "teenager": "young",
                    "middle-aged": "adult",
                    "middle_aged": "adult",
                    "none": "adult",
                    "null": "adult",
                    "unknown": "adult",
                },
            ),
            "tone": _normalize_enum_like(
                voice_profile.get("tone", "calm"),
                allowed={"calm", "energetic", "whisper", "deep"},
                default="calm",
                aliases={
                    "excited": "energetic",
                    "soft": "whisper",
                    "low": "deep",
                    "none": "calm",
                    "null": "calm",
                    "unknown": "calm",
                },
            ),
            "tts_engine": "auto",
            "voice_id": voice_profile.get("voice_id", None),
        }

        visual_profile = character.get("visual_profile") or {}
        if not isinstance(visual_profile, dict):
            visual_profile = {}
        visual_profile_normalized = {
            "appearance": str(visual_profile.get("appearance", f"Distinctive look for {name or 'the character'}")).strip()
            or f"Distinctive look for {name or 'the character'}",
            "clothing": str(visual_profile.get("clothing", "Practical story-appropriate clothing")).strip()
            or "Practical story-appropriate clothing",
            "style": _normalize_enum_like(
                visual_profile.get("style", "fantasy"),
                allowed={"fantasy", "cartoon", "realistic"},
                default="fantasy",
                aliases={
                    "anime": "cartoon",
                    "3d": "realistic",
                    "cinematic": "realistic",
                    "photo": "realistic",
                    "photorealistic": "realistic",
                    "none": "fantasy",
                    "null": "fantasy",
                    "unknown": "fantasy",
                },
            ),
        }

        original_id = str(character.get("character_id", "")).strip()
        if original_id:
            character_alias_to_id[original_id] = character_id
        if name:
            character_alias_to_id[name.lower()] = character_id

        characters_out.append(
            {
                "character_id": character_id,
                "name": name,
                "role": role,
                "personality": personality,
                "voice_profile": voice_profile_normalized,
                "visual_profile": visual_profile_normalized,
            }
        )

    scenes_out: List[Dict[str, Any]] = []
    line_counter = 1
    valid_character_ids = [character["character_id"] for character in characters_out]
    for scene_idx, scene in enumerate(scenes_in, start=1):
        if not isinstance(scene, dict):
            raise ValueError("each scene must be an object")

        dialogues_in = list(scene.get("dialogues") or [])
        dialogues_out: List[Dict[str, Any]] = []
        for line_idx, dialogue in enumerate(dialogues_in, start=1):
            if not isinstance(dialogue, dict):
                raise ValueError("each dialogue must be an object")

            char_ref = str(dialogue.get("character_id", "")).strip()
            if not char_ref:
                char_ref = str(dialogue.get("character", "")).strip()

            normalized_char_id = character_alias_to_id.get(
                char_ref, character_alias_to_id.get(char_ref.lower(), char_ref)
            )
            if normalized_char_id not in valid_character_ids:
                if not valid_character_ids:
                    raise ValueError("phase 1 state must contain at least one character")
                normalized_char_id = valid_character_ids[(line_counter - 1) % len(valid_character_ids)]

            dialogues_out.append(
                {
                    "line_id": f"line_{line_counter:02d}",
                    "character_id": normalized_char_id,
                    "text": str(dialogue.get("text", "")).strip(),
                    "emotion": str(dialogue.get("emotion", "neutral")).strip() or "neutral",
                }
            )
            line_counter += 1

        scenes_out.append(
            {
                "scene_id": f"scene_{scene_idx:02d}",
                "order": scene_idx,
                "title": str(scene.get("title", "")).strip(),
                "visual_description": str(scene.get("visual_description", "")).strip(),
                "mood": str(scene.get("mood", "")).strip(),
                "setting": str(scene.get("setting", "A cinematic story setting")).strip() or "A cinematic story setting",
                "duration_sec": int(scene.get("duration_sec", scene.get("duration_seconds", 30))),
                "dialogues": dialogues_out,
            }
        )

    now = _iso_now()
    normalized = {
        "meta": {
            "project_id": project_id,
            "user_prompt": raw.get("user_prompt", ""),
            "current_version": 1,
            "created_at": now,
            "last_updated": now,
            "status": "completed",
        },
        "story": {
            "title": str(raw.get("story", {}).get("title", "")).strip(),
            "genre": str(raw.get("story", {}).get("genre", "")).strip(),
            "tone": str(raw.get("story", {}).get("tone", "")).strip(),
            "theme": str(raw.get("story", {}).get("theme", "")).strip(),
            "summary": str(raw.get("story", {}).get("summary", "")).strip(),
        },
        "characters": characters_out,
        "scenes": scenes_out,
    }

    return normalized


def _build_messages(user_prompt: str) -> List[Any]:
    parser = PydanticOutputParser(pydantic_object=Phase1State)

    system_prompt = (
        "You are a story planning engine for an agentic video pipeline. "
        "Return JSON only. Do not include markdown. Do not include explanations. "
        "Output must contain exactly top-level keys: meta, story, characters, scenes. "
        "No additional keys are allowed at any level. "
        "Generate 1 to 5 characters and 3 to 6 scenes. "
        "Each scene must include dialogues and each dialogue must reference a valid character_id. "
        "Use deterministic IDs: char_01...char_NN, scene_01...scene_NN, line_01_01... "
        "Scene order must be sequential from 1. "
        "Choose coherent genre, tone, and theme inferred from user input. "
        "Keep durations between 5 and 180 seconds. "
        "Follow this schema exactly:\n"
        f"{parser.get_format_instructions()}"
    )

    user_prompt_text = (
        "Create a complete Phase 1 state for this user prompt:\n"
        f"{user_prompt}"
    )
    return [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt_text)]


def _invoke_once(user_prompt: str, project_id: str) -> Dict[str, Any]:
    llm, provider = _build_llm()
    logger.info("Generating Phase 1 state using provider: %s", provider)

    response = llm.invoke(_build_messages(user_prompt))
    content = response.content if hasattr(response, "content") else response
    if isinstance(content, list):
        content = "".join(
            str(block.get("text", "")) if isinstance(block, dict) else str(block)
            for block in content
        )

    if not isinstance(content, str) or not content.strip():
        raise Phase1GenerationError("LLM returned an empty response.")

    json_text = _extract_json_text(content)
    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError as exc:
        logger.error("Failed to decode model output as JSON.")
        raise Phase1GenerationError("LLM output was not valid JSON.") from exc

    if isinstance(payload, dict):
        payload.setdefault("user_prompt", user_prompt)

    normalized = _normalize_phase1_shape(payload, project_id=project_id)
    validated = Phase1State.model_validate(normalized)
    return validated.model_dump(mode="json")


def generate_phase1_state(user_prompt: str) -> Dict[str, Any]:
    """Generate a validated Phase 1 state dictionary from a user prompt.

    Args:
        user_prompt: Free-form user idea that should be expanded into a story.

    Returns:
        A strictly validated dictionary with keys: meta, story, characters, scenes.

    Raises:
        Phase1GenerationError: If provider setup, LLM output, or validation fails.
    """

    prompt = (user_prompt or "").strip()
    if not prompt:
        raise ValueError("user_prompt cannot be empty")

    project_id = str(uuid4())
    attempts = 2
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return _invoke_once(prompt, project_id=project_id)
        except (ValidationError, ValueError, Phase1GenerationError) as exc:
            last_error = exc
            logger.warning(
                "Phase 1 generation attempt %s/%s failed: %s",
                attempt,
                attempts,
                exc,
            )
            if attempt == attempts:
                break

    raise Phase1GenerationError(
        f"Failed to generate valid Phase 1 state after {attempts} attempts: {last_error}"
    )

