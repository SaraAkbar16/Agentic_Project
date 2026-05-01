"""CLI runner for Phase 3 - Video Generation & Composition."""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from agents.video_agent.agent import VideoAgent


def main():
    parser = argparse.ArgumentParser(description="Run Phase 3 - Video Generation")
    parser.add_argument("--phase1-state", type=str, help="Path to Phase 1 state JSON")
    parser.add_argument("--timing-manifest", type=str, help="Path to timing manifest JSON")
    parser.add_argument("--resolution", type=str, default="1280x720", help="Output resolution")
    parser.add_argument("--fps", type=int, default=24, help="Output FPS")
    parser.add_argument("--subtitles", action="store_true", help="Enable subtitle burning")
    parser.add_argument("--force", action="store_true", help="Force regeneration of frames (skip cache)")
    parser.add_argument("--comfy-url", type=str, help="ComfyUI URL (defaults to COMFY_URL env var)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )

    logger = logging.getLogger("phase3.cli")
    logger.info("Starting Phase 3 CLI")

    config = {
        "phase1_state_file": args.phase1_state,
        "timing_manifest_file": args.timing_manifest,
        "resolution": args.resolution,
        "fps": args.fps,
        "subtitles": args.subtitles,
        "force": args.force,
        "comfy_url": args.comfy_url,
    }

    try:
        agent = VideoAgent(config)
        state = agent.run()
        
        print("\n" + "="*50)
        print("PHASE 3 COMPLETE")
        print("="*50)
        print(f"Final Video: {state.outputs.final_video}")
        print(f"Total Scenes: {state.summary.total_scenes}")
        print(f"Total Duration: {state.summary.total_duration_seconds:.2f}s")
        print(f"Status: {state.status}")
        if state.errors:
            print(f"Errors encountered: {len(state.errors)}")
            for err in state.errors:
                print(f"  - {err}")
        print("="*50)
        
    except Exception as e:
        logger.error(f"Phase 3 failed: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
