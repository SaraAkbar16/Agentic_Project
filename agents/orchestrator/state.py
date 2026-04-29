"""Shared orchestrator state contracts.

These aliases keep Phase 1 outputs explicit for later graph integration.
"""

from __future__ import annotations

from typing import Any, Dict, TypedDict


class OrchestratorState(TypedDict, total=False):
	"""Minimal state contract used by orchestrator nodes."""

	user_prompt: str
	phase1_state: Dict[str, Any]

