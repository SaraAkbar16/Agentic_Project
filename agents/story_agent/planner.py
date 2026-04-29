"""Planner entry points for Phase 1 story generation."""

from __future__ import annotations

from typing import Any, Dict

from agents.story_agent.agent import generate_phase1_state


def plan_phase1_story(user_prompt: str) -> Dict[str, Any]:
    """Thin planner wrapper around the Phase 1 generation function.

    This wrapper keeps a stable call signature for future orchestration layers,
    including LangGraph nodes that can call planner functions directly.
    """

    return generate_phase1_state(user_prompt)

