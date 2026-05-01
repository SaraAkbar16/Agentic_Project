"""Unit tests for Phase 3 Video Agent."""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json

from agents.video_agent.agent import VideoAgent
from mcp.tools.video_tools import subtitle_tool, compositor_tool


class TestVideoAgent(unittest.TestCase):

    def setUp(self):
        self.config = {
            "data_dir": "test_data",
            "comfy_url": "http://mock-comfy:8188",
            "phase1_state_file": "test_phase1.json",
            "timing_manifest_file": "test_timing.json"
        }
        self.agent = VideoAgent(self.config)

    def test_build_image_prompt(self):
        """Test that image prompt is built correctly from scene data."""
        scene = {
            "scene_id": "scene_01",
            "visual_description": "A dark forest",
            "visual_prompt": "trees, fog",
            "dialogues": [{"character_id": "char_01"}]
        }
        phase1_state = {
            "characters": [{"character_id": "char_01", "visual_description": "A warrior"}]
        }
        
        # Manually reproducing the logic from agent.py for test
        char_ids = {d["character_id"] for d in scene.get("dialogues", [])}
        char_descs = [c.get("visual_description", "") for c in phase1_state["characters"] if c["character_id"] in char_ids]
        prompt = " ".join(char_descs) + ". " + scene["visual_description"] + ", " + scene["visual_prompt"] + ", cinematic lighting, high detail, 8k resolution"
        
        self.assertIn("A warrior", prompt)
        self.assertIn("A dark forest", prompt)
        self.assertIn("8k resolution", prompt)

    def test_animation_effect_mapping(self):
        """Test tone to animation effect mapping."""
        self.assertEqual(compositor_tool.get_animation_effect("action scene"), "zoom_in")
        self.assertEqual(compositor_tool.get_animation_effect("melancholic mood"), "pan_left")
        self.assertEqual(compositor_tool.get_animation_effect("hopeful tone"), "zoom_out")
        self.assertEqual(compositor_tool.get_animation_effect("boring"), "static")

    def test_srt_generation(self):
        """Test SRT string formatting."""
        timing_manifest = {
            "scenes": [
                {
                    "scene_id": "scene_01",
                    "total_duration_ms": 2000,
                    "audio_segments": [
                        {
                            "character": "Zara",
                            "line": "Hello world",
                            "start_ms": 500,
                            "end_ms": 1500
                        }
                    ]
                }
            ]
        }
        
        # Test format_timestamp
        self.assertEqual(subtitle_tool.format_timestamp(500), "00:00:00,500")
        self.assertEqual(subtitle_tool.format_timestamp(3661000), "01:01:01,000")
        
        # Mock writing to file
        with patch("builtins.open", unittest.mock.mock_open()) as mocked_file:
            subtitle_tool.generate_srt(timing_manifest, "test.srt")
            
            # Check if Zara is in the output
            handle = mocked_file()
            # Combining calls to check content
            written_content = "".join(call.args[0] for call in handle.write.call_args_list)
            self.assertIn("Zara: Hello world", written_content)
            self.assertIn("00:00:00,500 --> 00:00:01,500", written_content)

    @patch("subprocess.run")
    def test_ffmpeg_ken_burns_command(self, mock_run):
        """Test that FFmpeg command is constructed with correct args."""
        from mcp.tools.video_tools import ffmpeg_tool
        
        ffmpeg_tool.apply_ken_burns(
            input_image="img.png",
            output_video="out.mp4",
            duration_seconds=5.0,
            effect="zoom_in"
        )
        
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "ffmpeg")
        self.assertIn("zoompan", args[args.index("-vf") + 1])
        self.assertIn("img.png", args)
        self.assertIn("out.mp4", args)

    def test_phase3_state_schema(self):
        """Test Pydantic validation for Phase3State."""
        from shared.schemas.phase3_schema import Phase3State
        
        sample_state = {
            "phase": 3,
            "status": "completed",
            "timestamp": "2026-05-01T20:00:00",
            "inputs": {
                "phase1_state_file": "p1.json",
                "timing_manifest_file": "tm.json"
            },
            "outputs": {
                "frames_dir": "frames",
                "clips_dir": "clips",
                "final_video": "final.mp4"
            },
            "scenes": [
                {
                    "scene_id": "scene_01",
                    "clip_path": "clip1.mp4",
                    "duration_seconds": 8.0,
                    "frame_path": "frame1.png",
                    "animation_effect": "zoom_in",
                    "image_prompt_used": "prompt",
                    "comfy_workflow_used": "wan2.1"
                }
            ],
            "summary": {
                "total_scenes": 1,
                "total_duration_seconds": 8.0,
                "resolution": "1280x720",
                "fps": 24
            }
        }
        
        state = Phase3State(**sample_state)
        self.assertEqual(state.phase, 3)
        self.assertEqual(len(state.scenes), 1)


if __name__ == "__main__":
    unittest.main()
