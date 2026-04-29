"""Run Phase 1 generation from CLI and save JSON output to disk."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

# Ensure imports work when running this file directly from scripts/.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.story_agent.agent import generate_phase1_state


def main() -> None:
    prompt = input("Enter your story prompt: ").strip()
    if not prompt:
        raise SystemExit("Prompt cannot be empty.")

    result = generate_phase1_state(prompt)

    output_dir = Path("data") / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"phase1_state_{timestamp}.json"
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"Saved JSON output to: {output_path}")


if __name__ == "__main__":
    main()
