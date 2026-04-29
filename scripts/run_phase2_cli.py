"""CLI entrypoint for Phase 2 audio generation.

Usage:
    python scripts/run_phase2_cli.py <path_to_phase1_json>

All outputs are written into the same directory as the input file.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime

import sys
import os

# Ensure repository root is on sys.path so `agents` imports work when run
# from scripts/ in a variety of environments.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.audio_agent.agent import run_phase2_on_file


def _output_filename_for(input_path: str) -> str:
    base = os.path.basename(input_path)
    parent = os.path.dirname(input_path)
    if base.startswith("phase1_state_"):
        new_name = base.replace("phase1_state_", "phase2_state_")
    else:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        new_name = f"phase2_state_{ts}.json"
    return os.path.join(parent, new_name)


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv or len(argv) != 1:
        print("Usage: python scripts/run_phase2_cli.py <phase1_json_path>")
        return 2

    phase1_path = argv[0]
    if not os.path.isfile(phase1_path):
        print(f"Error: file not found: {phase1_path}")
        return 3

    # Run Phase 2
    phase2 = run_phase2_on_file(phase1_path)

    outpath = _output_filename_for(phase1_path)
    with open(outpath, "w", encoding="utf-8") as fh:
        json.dump(phase2, fh, indent=2, ensure_ascii=False)

    print(f"Saved Phase 2 JSON to: {outpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
